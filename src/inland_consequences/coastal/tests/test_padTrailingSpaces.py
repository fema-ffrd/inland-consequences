from inland_consequences.coastal import _pfracoastal_lib

def test_use_default_out_len():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_str = "test"
    out_len = 0
    
    ret = lib.padTrailingSpaces(inText=test_str, tLength=out_len)
    assert ret == test_str
    
def test_use_inText_len_as_out_len():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_str = "test"
    out_len = 4
    
    ret = lib.padTrailingSpaces(inText=test_str, tLength=out_len)
    assert ret == test_str
    
def test_use_greater_out_len_than_inText_len():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_str = "test"
    out_len = 8
    
    ret = lib.padTrailingSpaces(inText=test_str, tLength=out_len)
    assert ret == "test    "

