"""Only player resources, never scheduling or branch-state variables."""
from decimal import Decimal,ROUND_HALF_UP,ROUND_CEILING
import re
from pdxscript import blocks,apply_edits
def fmt(x):return f'{x.normalize():f}'
def adjust(option):
    changes=[];edits=[]
    for _,_,s,e,_ in (b for b in blocks(option) if b[0]=='change_variable'):
        body=option[s:e];name=re.search(r'\bname\s*=\s*(hbe_(?:yiqi|guoqi|burden))\b',body)
        m=re.search(r'\b(add|subtract)\s*=\s*(-?\d+(?:\.\d+)?)',body)
        if not name or not m:continue
        value=Decimal(m[2]);delta=value if m[1]=='add' else -value
        good=delta<0 if name[1]=='hbe_burden' else delta>0
        magnitude=abs(value)
        new=(magnitude*Decimal('.7')).quantize(Decimal(1),rounding=ROUND_HALF_UP) if good else (magnitude*Decimal('1.5')).quantize(Decimal(1),rounding=ROUND_CEILING)
        if value<0:new=-new
        edits.append((s+m.start(2),s+m.end(2),fmt(new)))
        changes.append(dict(variable=name[1],operation=m[1],before=fmt(value),after=fmt(new),beneficial=good))
    option=apply_edits(option,edits)
    for row in changes:
        if row['operation']=='subtract' and row['variable']!='hbe_burden' and Decimal(row['before'])>0:
            option=re.sub(r'\bvar:'+row['variable']+r'\s*>=\s*'+re.escape(row['before'])+r'\b','var:'+row['variable']+' >= '+row['after'],option)
    edits=[]
    for _,_,s,e,_ in (b for b in blocks(option) if b[0]=='add_estate_satisfaction'):
        body=option[s:e]
        body=re.sub(r'\bvalue\s*=\s*-(\d+(?:\.\d+)?)',lambda m:'value = -'+fmt((Decimal(m[1])*Decimal('1.5')).quantize(Decimal('.01'),rounding=ROUND_CEILING)),body)
        edits.append((s,e,body))
    return apply_edits(option,edits),changes
