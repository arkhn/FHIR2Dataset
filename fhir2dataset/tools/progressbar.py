def progressbar(func):
    """Decorator for class methods that update a progressbar

    The class should have the following attributes:
    - pbar: the tqdm progressbar
    - bar_frac (float): the fraction of this bar allocated to the class instance
    - number_calls (int): the expected number of iterations made in this instance
    """

    def _progressbar(self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        if hasattr(self, "pbar") and self.pbar is not None:
            if hasattr(self, "number_calls") and self.number_calls is not None:
                bar_frac_per_call = self.bar_frac / self.number_calls
                self.pbar.update(bar_frac_per_call)

        return result

    return _progressbar
