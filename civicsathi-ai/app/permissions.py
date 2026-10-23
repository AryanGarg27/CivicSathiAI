ALLOWED={'citizen':{'intake','submit','view'},'staff':{'intake','submit','view','update'}}
class PermissionDenied(Exception): pass
def require(role,action):
    if action not in ALLOWED.get(role,set()): raise PermissionDenied(f'{role} cannot perform {action}')
