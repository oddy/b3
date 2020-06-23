
# B3 Usage examples

# See the test_comp tests for more examples.

# --- Simple recursive datastructure packing (like json.dumps) ---

from pprint import pprint
import decimal, datetime

import b3

# You can pack lists of things:

list_data = [ None,  b"foo",  u"bar",  True,  -69,  2.318,  46j,  [1,2,3],  {4:5, 6:7},
              decimal.Decimal("13.37"), datetime.datetime.now() ]

list_buf = b3.pack(list_data)

# Complex numbers, decimal numbers, and dates and times all work.

# You can pack dicts of things:

dict_data = { 1:1, u"2":u"2", b"3":b"3" }

dict_buf = b3.pack(dict_data)



print(len(buf))

out_data = b3.unpack(buf, 0)

pprint(out_data)


# pack and unpack a bunch of stuff.
# unpack_into ?

# schema pack and unpack

# nested schema messages.


