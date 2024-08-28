from datetime import timedelta


def timedelta_formatter(td: timedelta):
    if isinstance(td, timedelta):
        td_sec = td.seconds
        hours, rem = divmod(td_sec, 3600)
        minutes, seconds = divmod(rem, 60)
        td_print = "{}d {}h {}m".format(td.days, hours, minutes)
        return td_print
