from click import Option, UsageError


# See https://stackoverflow.com/a/37491504/499285 and https://stackoverflow.com/a/44349292/499285
class MutuallyExclusiveOption(Option):
    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop("mutually_exclusive", []))
        help = kwargs.get("help", "")
        if self.mutually_exclusive:
            kwargs["help"] = help + f" Mutually exclusive with {', '.join(self.mutually_exclusive)}."
        super().__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        self_present = self.name in opts
        others_present = self.mutually_exclusive.intersection(opts)

        if others_present:
            if self_present:
                raise UsageError(
                    f"Illegal usage: {self.name} is mutually exclusive with {', '.join(self.mutually_exclusive)}."
                )
            else:
                self.prompt = None

        return super().handle_parse_result(ctx, opts, args)
