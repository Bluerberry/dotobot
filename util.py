
# Wraps around commands to split args into flags and params.
# Recieving function MUST follow func(ctx, flags, params, *args, **kwargs)

def extract_flags(func):
    async def wrapper(ctx, *args, **_):
        flags = []
        params = []

        for arg in list(args):
            if arg.startswith('--'):
                flags.append(arg[2:])
            else:
                params.append(arg)

        return await func(ctx, flags, params)
    return wrapper
