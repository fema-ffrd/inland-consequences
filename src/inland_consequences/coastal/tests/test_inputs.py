from inland_consequences.coastal import pfracoastal
import logging 

logger = logging.getLogger(__name__)

def test_Inputs():
    logging.basicConfig(filename="inputsTest.log", level=logging.INFO)
    
    correct_attr_dict = {
        "blabber":True, 
        "use_heatmap":True, 
        "hm_bandwidth":1100, 
        "hm_resolution":500, 
        "hm_name":"heatmap",
        "mc_n":2000, 
        "nbounds":tuple([0.0001, 1]), 
        "storm_csv":'', 
        "bldg_path":'', 
        "bldg_lay":None,
        "swel_mpath":'', 
        "swel_path":'', 
        "swelA_path":'', 
        "swelB_path":'', 
        "waveA_path":'', 
        "waveB_path":'', 
        "use_uncertainty":True,
        "use_cutoff":True,
        "use_cutoff10":False, 
        "use_eWet":True, 
        "use_waves":True, 
        "use_twl":False, 
        "use_wavecut50":False, 
        "use_erosion":False,
        "use_singleloss":False, 
        "use_insurance":False, 
        "use_contents":False, 
        "use_netcdf":False, 
        "use_outcsv":False, 
        "bddf_lut_path":'',
        "bldg_ddf_lut":None, 
        "cddf_lut_path":None, 
        "cont_ddf_lut":None, 
        "proj_prefix":'', 
        "out_shp_path":'',
        "GCB_fid":'location', 
        "GCB_Bded":'BLDG_DED', 
        "GCB_Blim":'BLDG_LIMIT', 
        "GCB_Bval":'BLDG_VALUE', 
        "GCB_Cded":'CNT_DED', 
        "GCB_Clim":'CNT_LIM', 
        "GCB_Cval":'CNT_VALUE', 
        "GCB_Bsto":'NUM_STORIE', 
        "GCB_Bfou":'foundation',
        "GCB_Bbfi":'BasementFi', 
        "GCB_Bffh":'FIRST_FLOO', 
        "GCB_Bdem":'DEMft'
    }
    
    test_inputs_obj = pfracoastal.Inputs()
    test_inputs_obj_dict = test_inputs_obj.__dict__
    
    logger.info("============================= TEST START ============================")
    logger.info("Comparing test object attributes with correct attr dict values...")
    keys = correct_attr_dict.keys()
    mismatch_count = 0
    for key in keys:
        if test_inputs_obj_dict[key] != correct_attr_dict[key]:
            mismatch_count += 1
            logger.info(f"WARNING: test_inputs_obj.{key} value '{test_inputs_obj_dict[key]}' doesn't match comparison value '{correct_attr_dict[key]}'.")
    
    if mismatch_count == 0:
        logger.info('Success! No attribute mismatches found.')
    
    logging.shutdown()
    assert test_inputs_obj_dict == correct_attr_dict