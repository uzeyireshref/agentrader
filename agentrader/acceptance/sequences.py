"""Seeded order-event sequences and bounded failure minimization."""
import random


def generate(seed, steps=80):
    if type(seed) is not int or not 0<=seed<2**32 or type(steps) is not int or not 1<=steps<=500:
        raise ValueError('ACCEPTANCE_SEQUENCE_ARGUMENT_INVALID')
    rng=random.Random(seed);trace=[]
    for i in range(steps):
        kind=rng.choices(['observe','duplicate','restart','conflict','foreign','identity'],[50,15,12,8,8,7])[0]
        item={'kind':kind,'order':rng.randrange(3)}
        if kind=='observe':
            fill=rng.randrange(11);status=rng.choice(['NEW','PARTIALLY_FILLED','CANCELED','EXPIRED','REJECTED','FILLED'])
            if status in ('NEW','REJECTED'):fill=0
            if status=='FILLED':fill=10
            item.update(event=f'e{i}',status=status,fill=fill,at=rng.randrange(1,1000))
        trace.append(item)
    return trace


def minimize(trace, fails, max_runs=128):
    """Remove chunks while preserving the caller's same-failure predicate.

    This is bounded delta debugging, not a claim of globally minimal traces.
    Every predicate run must use fresh isolated state.
    """
    if type(max_runs) is not int or not 1<=max_runs<=1000:raise ValueError('ACCEPTANCE_SHRINK_BUDGET_INVALID')
    current=list(trace);runs=0;parts=2
    while len(current)>1 and runs<max_runs:
        size=(len(current)+parts-1)//parts;reduced=False
        for start in range(0,len(current),size):
            candidate=current[:start]+current[start+size:]
            if not candidate:continue
            runs+=1
            if fails(candidate):current=candidate;parts=max(2,parts-1);reduced=True;break
            if runs>=max_runs:break
        if not reduced:
            if parts>=len(current):break
            parts=min(len(current),parts*2)
    return {'trace':current,'attempts':runs,'one_minimal_proven':False}
