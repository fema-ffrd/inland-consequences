#import _pfracoastal_lib
from inland_consequences.coastal import _pfracoastal_lib

def test_removeNonNumeric():
    #test_str = 'test value is -3.14'
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    ret = lib.removeNonNumeric('test value is -3.14')
    assert ret == '-3.14' 