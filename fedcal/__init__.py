# fedcal __init__.py
#
# Copyright (c) 2023 Adam Poulemanos. All rights reserved.
#
# fedcal is open source software subject to the terms of the
# MIT license, found in the
# [GitHub source directory](https://github.com/psuedomagi/fedcal)
# in the LICENSE.md file.
#
# It may be freely distributed, reused, modified, and distributed under the
# terms of that license, but must be accompanied by the license and the
# accompanying copyright notice.

"""
Welcome to fedcal!

fedcal's __init__.py. Nothing extraordinary here. We import and name the primary API modules, `FedIndex` and `FedStamp` and their helper functions,
`to_fedstamp` and `to_fedindex`. This makes them easy to import and use, like:

```python
from fedcal import to_fedindex
dates = ((1999,10,1), (2040,9,30))
index = to_fedindex(dates)
```

We also import the `FedDepartment` class and the `Dept` enum, which are used to create a `FedDepartment` object. Which may be useful depending on what
kind of analysis you are doing.
"""

from .fedindex import FedIndex, to_fedindex
from .fedstamp import FedStamp, to_fedstamp
from .depts import FedDepartment
from .constants import Dept

__all__: list[str] = [
    "FedStamp",
    "FedIndex",
    "to_fedstamp",
    "to_fedindex",
    "FedDepartment",
    "Dept",
]
