from inland_consequences.coastal import _pfracoastal_lib

def test_getZscore():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_x = 100.0
    test_mean = 80.0
    test_sd = 2.0
    
    ret = lib.getZscore(test_x, test_mean, test_sd)
    assert ret == 10.0