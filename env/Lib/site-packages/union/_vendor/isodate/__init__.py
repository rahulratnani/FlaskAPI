"""
Vendored from https://github.com/gweis/isodate

Copyright (c) 2021, Hugo van Kemenade and contributors
Copyright (c) 2009-2018, Gerhard Weis and contributors
Copyright (c) 2009, Gerhard Weis
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

import re
from datetime import timedelta

STRF_D_MAP = {
    "%d": lambda tdt, yds: "%02d" % tdt.days,
    "%f": lambda tdt, yds: "%06d" % tdt.microseconds,
    "%H": lambda tdt, yds: "%02d" % (tdt.seconds / 60 / 60),
    "%m": lambda tdt, yds: "%02d" % tdt.months,
    "%M": lambda tdt, yds: "%02d" % ((tdt.seconds / 60) % 60),
    "%S": lambda tdt, yds: "%02d" % (tdt.seconds % 60),
    "%W": lambda tdt, yds: "%02d" % (abs(tdt.days / 7)),
    "%Y": lambda tdt, yds: (((yds != 4) and "+") or "") + (("%%0%dd" % yds) % tdt.years),
    "%C": lambda tdt, yds: (((yds != 4) and "+") or "") + (("%%0%dd" % (yds - 2)) % (tdt.years / 100)),
    "%%": lambda tdt, yds: "%",
}


def _strfduration(tdt, format, yeardigits=4):
    """
    this is the work method for timedelta and Duration instances.

    see strftime for more details.
    """

    def repl(match):
        """
        lookup format command and return corresponding replacement.
        """
        if match.group(0) in STRF_D_MAP:
            return STRF_D_MAP[match.group(0)](tdt, yeardigits)
        elif match.group(0) == "%P":
            ret = []
            usecs = abs((tdt.days * 24 * 60 * 60 + tdt.seconds) * 1000000 + tdt.microseconds)
            seconds, usecs = divmod(usecs, 1000000)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)
            if days:
                ret.append("%sD" % days)
            if hours or minutes or seconds or usecs:
                ret.append("T")
                if hours:
                    ret.append("%sH" % hours)
                if minutes:
                    ret.append("%sM" % minutes)
                if seconds or usecs:
                    if usecs:
                        ret.append(("%d.%06d" % (seconds, usecs)).rstrip("0"))
                    else:
                        ret.append("%d" % seconds)
                    ret.append("S")
            # at least one component has to be there.
            return ret and "".join(ret) or "0D"
        elif match.group(0) == "%p":
            return str(abs(tdt.days // 7)) + "W"
        return match.group(0)

    return re.sub("%d|%f|%H|%m|%M|%S|%W|%Y|%C|%%|%P|%p", repl, format)


D_DEFAULT = "P%P"


def duration_isoformat(tduration, format=D_DEFAULT):
    """
    Format duration strings.

    This method is just a wrapper around isodate.isostrf.strftime and uses
    P%P (D_DEFAULT) as default format.
    """
    # TODO: implement better decision for negative Durations.
    #       should be done in Duration class in consistent way with timedelta.
    if isinstance(tduration, timedelta) and (tduration < timedelta(0)):
        ret = "-"
    else:
        ret = ""
    ret += _strfduration(tduration, format)
    return ret
