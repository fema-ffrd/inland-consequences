from inland_consequences.coastal import _pfracoastal_lib

def test_adjust_Loss_DEDLIM1():
    lib = _pfracoastal_lib._PFRACoastal_Lib()
    
    test_loss = 25_000
    test_ded = 5000
    test_lim = 250_000
    
    ret = lib.adjust_Loss_DEDLIM1(loss=test_loss, ded=test_ded, lim=test_lim)
    assert ret == 20_000