"""EU5 schema adapter; no HBE tag lists or gameplay assumptions in this layer."""
from dataclasses import dataclass
from decimal import Decimal
from .source import SaveSource
from .syntax import Syntax,Block,Scalar,json_value
from .errors import SchemaError


def number(value,label,default=None):
    if value is None:return default
    if isinstance(value,bool) or not isinstance(value,(int,Decimal,float)):
        raise SchemaError(f'{label} must be numeric, got {value!r}')
    return float(value)


def scalar_list(block):
    if block is None:return []
    result=[]
    for item in block.list_values():
        if not isinstance(item,Scalar):raise SchemaError('Expected scalar list item')
        result.append(json_value(item))
    return result


@dataclass(frozen=True)
class Variable:
    kind:str
    identity:int
    value:object
    implicit_zero:bool
    tick:object=None


def read_variables(owner):
    variables=owner.block('variables')
    if variables is None:return {}
    data=variables.block('data')
    if data is None:return {}
    result={}
    for entry in data.entries:
        record=entry.value
        if not isinstance(record,Block):raise SchemaError('Variable record must be a block')
        flag=record.scalar('flag')
        if not isinstance(flag,str):raise SchemaError('Variable has no scalar flag name')
        if flag in result:raise SchemaError('Duplicate variable flag: '+flag)
        value=record.block('data',required=True);kind=value.scalar('type')
        if kind is None and not value.entries:kind='none'
        if not isinstance(kind,str):raise SchemaError('Variable has no type: '+flag)
        identity=value.scalar('identity',0)
        if isinstance(identity,bool) or not isinstance(identity,int):raise SchemaError('Variable identity must be an integer: '+flag)
        implicit=value.one('identity') is None
        if kind=='none':
            if identity!=0:raise SchemaError('Empty variable unexpectedly has an identity: '+flag)
            decoded=None
        elif kind=='value':
            # Native fixed point uses signed 64-bit storage and omits zero identity.
            if not -(2**63)<=identity<2**64:raise SchemaError('Fixed-point identity outside 64-bit range')
            signed=identity-2**64 if identity>=2**63 else identity
            decoded=Decimal(signed)/Decimal(100000)
        elif kind=='boolean':
            if identity not in (0,1):raise SchemaError('Boolean variable is not 0 or 1: '+flag)
            decoded=bool(identity)
        else:
            # Unknown/reference types are preserved, never divided by the value scale.
            decoded=dict(type=kind,id=identity)
        result[flag]=Variable(kind,identity,decoded,implicit,record.scalar('tick'))
    return result


def variable_values(owner):
    return {k:json_value(v.value) for k,v in read_variables(owner).items()}


class EU5Save:
    def __init__(self,path,**limits):
        self.source=SaveSource(path,max_bytes=limits.pop('max_bytes',2*1024**3))
        try:self.syntax=Syntax(self.source,**limits);self.root=self.syntax.root
        except BaseException:self.source.close();raise

    @classmethod
    def from_bytes(cls,data,**limits):
        obj=cls.__new__(cls);obj.source=SaveSource.from_bytes(data)
        obj.syntax=Syntax(obj.source,**limits);obj.root=obj.syntax.root
        return obj

    @property
    def metadata(self):
        meta=self.root.block('metadata')
        if meta is None and self.source.zip_metadata:
            extra=Syntax(SaveSource.from_bytes(self.source.zip_metadata))
            meta=extra.root.block('metadata') or extra.root
        meta=meta or self.root
        return dict(date=json_value(meta.scalar('date')),playthrough_id=meta.scalar('playthrough_id'),format=self.source.format)

    def records(self,name):
        container=self.root.block(name)
        if container is None:return {}
        database=container.block('database') or container
        result={};seen=set()
        for entry in database.entries:
            if entry.key is None or not entry.key.isdecimal():continue
            ident=int(entry.key)
            if ident in seen:raise SchemaError(f'Duplicate {name} ID {ident}')
            seen.add(ident)
            if isinstance(entry.value,Scalar) and not entry.value.quoted and entry.value.text=='none':
                continue # Native database tombstone; retained in the syntax layer.
            if not isinstance(entry.value,Block):raise SchemaError(f'{name} record {entry.key} is not a block')
            result[ident]=entry.value
        return result

    @property
    def tags(self):
        container=self.root.block('countries')
        tags=container.block('tags') if container else None
        if tags is None:return {}
        result={}
        for e in tags.entries:
            if e.key is None or not e.key.isdecimal() or not isinstance(e.value,Scalar):raise SchemaError('Invalid country tag table')
            ident=int(e.key)
            if ident in result:raise SchemaError('Duplicate country tag ID')
            result[ident]=e.value.text
        return result

    def countries(self,ids=None):
        tags=self.tags
        for ident,b in self.records('countries').items():
            if ids is not None and ident not in ids:continue
            money=b.block('currency_data');econ=b.block('economy');gov=b.block('government')
            researched=b.block('researched_advances')
            def field(section,key):return number(section.scalar(key,0),key) if section else None
            definition=b.scalar('definition',tags.get(ident))
            if not isinstance(definition,str):raise SchemaError(f'Country {ident} has no tag')
            owned=scalar_list(b.block('owned_locations'))
            if any(isinstance(x,bool) or not isinstance(x,int) for x in owned):raise SchemaError('Owned locations must be integer IDs')
            types=read_variables(b)
            ruler=b.scalar('ruler')
            if ruler is None and gov:ruler=gov.scalar('ruler')
            yield dict(id=ident,tag=definition,locations=len(owned),owned_locations=owned,
                       gold=field(money,'gold'),prestige=field(money,'prestige'),stability=field(money,'stability'),
                       income=field(econ,'income'),expense=field(econ,'expense'),
                       population=number(b.scalar('last_months_population'),'population'),
                       ruler=ruler,regent=gov.scalar('active_regent') if gov else None,
                       techs=[e.key for e in researched.entries if e.key and isinstance(e.value,Scalar) and e.value.value is True] if researched else [],
                       variables={k:json_value(v.value) for k,v in types.items()},
                       variable_types={k:v.kind for k,v in types.items() if v.kind not in ('value','boolean')})

    def organizations(self):
        for ident,b in self.records('international_organization_manager').items():
            yield dict(id=ident,type=b.scalar('type'),members=scalar_list(b.block('all_members')),
                       leader=b.scalar('leader_country'),variables=variable_values(b))

    def buildings(self,prefix=None):
        for ident,b in self.records('building_manager').items():
            kind=b.scalar('type')
            if prefix is not None and (not isinstance(kind,str) or not kind.startswith(prefix)):continue
            yield dict(id=ident,type=kind,owner=b.scalar('owner'),location=b.scalar('location'),
                       level=number(b.scalar('level',0),'level'),employed=number(b.scalar('employed',0),'employed'),
                       profit=number(b.scalar('last_months_profit',0),'last_months_profit'))

    def units(self,prefix=None):
        for ident,b in self.records('subunit_manager').items():
            kind=b.scalar('type')
            if prefix is not None and (not isinstance(kind,str) or not kind.startswith(prefix)):continue
            yield dict(id=ident,type=kind,owner=b.scalar('owner'),unit=b.scalar('unit'))

    def goods(self,prefix=None):
        manager=self.root.block('market_manager');goods=manager.block('produced_goods') if manager else None
        if goods is None:return {}
        result={}
        for entry in goods.entries:
            if prefix is not None and not (entry.key or '').startswith(prefix):continue
            if entry.key is None or not isinstance(entry.value,Scalar):raise SchemaError('Invalid produced goods entry')
            if entry.key in result:raise SchemaError('Duplicate goods entry')
            result[entry.key]=number(entry.value.value,entry.key)
        return result

    def wars(self):
        def participants(block):
            result=set()
            for entry in block.entries:
                if entry.key=='country' and isinstance(entry.value,Scalar):
                    value=entry.value.value
                    if isinstance(value,int) and not isinstance(value,bool):result.add(value)
                elif isinstance(entry.value,Block):result.update(participants(entry.value))
            return result
        for ident,b in self.records('war_manager').items():
            yield dict(id=ident,participants=sorted(participants(b)),start=json_value(b.scalar('start_date')))

    def validate(self):
        self.root.validate();self.source.assert_unchanged()

    def close(self):self.source.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
