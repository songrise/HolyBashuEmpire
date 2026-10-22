"""Lazy Clausewitz/Jomini syntax. Preserve order, duplicate keys and list items."""
from dataclasses import dataclass
from decimal import Decimal
import re
from .errors import SaveSyntaxError, AmbiguousKey, SchemaError

_SPACE=re.compile(rb'(?:\s+|#[^\r\n]*(?:\r\n|\r|\n|$))*')
_COMMENT=re.compile(rb'#[^\r\n]*(?:\r\n|\r|\n|$)')
_ATOM=re.compile(rb'[^\s{}=<>!?#"]+')
_STRING=re.compile(rb'"(?:[^"\\]|\\.)*"',re.S)
_SPECIAL=re.compile(rb'["#{}]')
_NUMBER=re.compile(r'[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?\Z')
_DATE=re.compile(r'\d+\.\d+\.\d+\Z')


@dataclass(frozen=True,order=True)
class GameDate:
    year:int
    month:int
    day:int
    def __str__(self): return f'{self.year}.{self.month}.{self.day}'


@dataclass(frozen=True)
class Scalar:
    text:str
    quoted:bool=False
    @property
    def value(self):
        if self.quoted:return self.text
        if self.text in ('yes','no'):return self.text=='yes'
        if _DATE.fullmatch(self.text):return GameDate(*map(int,self.text.split('.')))
        if re.fullmatch(r'[+-]?\d+',self.text):return int(self.text)
        if _NUMBER.fullmatch(self.text):return Decimal(self.text)
        return self.text


@dataclass(frozen=True)
class Tagged:
    tag:str
    block:'Block'


@dataclass(frozen=True)
class Entry:
    key:str|None
    operator:str|None
    value:object


class Syntax:
    def __init__(self,source,*,max_depth=512,max_scalar_bytes=2*1024**2):
        self.source=source;self.data=source.data;self.max_depth=max_depth
        self.max_scalar_bytes=max_scalar_bytes;self.ends={}
        self.root=Block(self,source.start,len(self.data))

    def skip_space(self,pos,end):return _SPACE.match(self.data,pos,end).end()

    def scalar(self,pos,end):
        quoted=self.data[pos:pos+1]==b'"'
        m=(_STRING if quoted else _ATOM).match(self.data,pos,end)
        if not m:raise SaveSyntaxError('Expected scalar or terminated quoted string',pos)
        if m.end()-pos>self.max_scalar_bytes:raise SaveSyntaxError('Scalar exceeds configured limit',pos)
        raw=bytes(self.data[pos+1:m.end()-1] if quoted else self.data[pos:m.end()])
        if b'\0' in raw:raise SaveSyntaxError('NUL byte in text scalar',pos)
        try:text=raw.decode('utf-8')
        except UnicodeDecodeError as exc:raise SaveSyntaxError('Invalid UTF-8 text',pos) from exc
        if quoted:
            # Preserve unknown escape sequences rather than silently dropping a slash.
            text=re.sub(r'\\(["\\nrt])',lambda m:{'n':'\n','r':'\r','t':'\t'}.get(m[1],m[1]),text)
        return Scalar(text,quoted),m.end()

    def block_end(self,opening,end):
        cached=self.ends.get(opening)
        if cached is not None:return cached
        depth=1;pos=opening+1
        while pos<end:
            m=_SPECIAL.search(self.data,pos,end)
            if not m:break
            pos=m.start();value=self.data[pos:pos+1]
            if value==b'"':
                q=_STRING.match(self.data,pos,end)
                if not q:raise SaveSyntaxError('Unterminated quoted string',pos)
                if q.end()-pos>self.max_scalar_bytes:raise SaveSyntaxError('Quoted string exceeds limit',pos)
                pos=q.end();continue
            if value==b'#':
                pos=_COMMENT.match(self.data,pos,end).end();continue
            depth+=1 if value==b'{' else -1
            if depth>self.max_depth:raise SaveSyntaxError('Maximum nesting depth exceeded',pos)
            if depth==0:self.ends[opening]=pos;return pos
            pos+=1
        raise SaveSyntaxError('Truncated or unclosed block',opening)

    def read_value(self,pos,end):
        pos=self.skip_space(pos,end)
        if pos>=end:raise SaveSyntaxError('Missing value',pos)
        if self.data[pos:pos+1]==b'{':
            close=self.block_end(pos,end);return Block(self,pos+1,close),close+1
        atom,nextpos=self.scalar(pos,end)
        look=self.skip_space(nextpos,end)
        if not atom.quoted and isinstance(atom.value,str) and self.data[look:look+1]==b'{':
            close=self.block_end(look,end)
            return Tagged(atom.text,Block(self,look+1,close)),close+1
        return atom,nextpos


class Block:
    def __init__(self,syntax,start,end):
        self.syntax=syntax;self.start=start;self.end=end;self._entries=None;self._keys=None

    @property
    def entries(self):
        if self._entries is None:
            s=self.syntax;pos=self.start;items=[]
            while True:
                pos=s.skip_space(pos,self.end)
                if pos>=self.end:break
                if s.data[pos:pos+1]==b'}':raise SaveSyntaxError('Unexpected closing brace',pos)
                first,pos=s.read_value(pos,self.end);look=s.skip_space(pos,self.end)
                op=None
                for candidate in (b'?=',b'<=',b'>=',b'!=',b'==',b'=',b'<',b'>'):
                    if s.data[look:look+len(candidate)]==candidate:op=candidate.decode();break
                if op:
                    if not isinstance(first,Scalar):raise SaveSyntaxError('Assignment key is not scalar',look)
                    value,pos=s.read_value(look+len(op),self.end)
                    items.append(Entry(first.text,op,value))
                else:items.append(Entry(None,None,first))
            self._entries=tuple(items)
        return self._entries

    def all(self,key):
        if self._keys is None:
            keys={}
            for entry in self.entries:
                if entry.key is not None:keys.setdefault(entry.key,[]).append(entry.value)
            self._keys=keys
        return tuple(self._keys.get(str(key),()))

    def one(self,key,default=None):
        values=self.all(key)
        if len(values)>1:raise AmbiguousKey(f'Duplicate key {key!r}; use all() explicitly')
        return values[0] if values else default

    def block(self,key,*,required=False):
        result=self.one(key)
        if result is None and not required:return None
        if not isinstance(result,Block):raise SchemaError(f'{key!r} must be a block')
        return result

    def scalar(self,key,default=None):
        value=self.one(key)
        if value is None:return default
        if not isinstance(value,Scalar):raise SchemaError(f'{key!r} must be a scalar')
        return value.value

    def list_values(self):
        if any(e.key is not None for e in self.entries):raise SchemaError('Expected anonymous list')
        return tuple(e.value for e in self.entries)

    def validate(self,depth=0):
        if depth>self.syntax.max_depth:raise SaveSyntaxError('Maximum semantic depth exceeded',self.start)
        for entry in self.entries:
            value=entry.value.block if isinstance(entry.value,Tagged) else entry.value
            if isinstance(value,Block):value.validate(depth+1)


def json_value(value):
    if isinstance(value,Scalar):return json_value(value.value)
    if isinstance(value,Decimal):return float(value)
    if isinstance(value,GameDate):return str(value)
    if isinstance(value,Tagged):return dict(tag=value.tag,entries=json_value(value.block))
    if isinstance(value,Block):return [dict(key=e.key,operator=e.operator,value=json_value(e.value)) for e in value.entries]
    return value
