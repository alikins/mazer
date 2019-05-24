

def uniq(seq):
    '''Order preserving list/iterable uniq'ifier'''
    seen = set()
    return [item for item in seq if item not in seen and not seen.add(item)]
