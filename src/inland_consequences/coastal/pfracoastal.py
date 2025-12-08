import rasterio
import geopandas as gpd
import pandas as pd
import numpy as np
import scipy
import logging
import typing
import multiprocessing
import os
from _pfracoastal_lib import _PFRACoastal_Lib

class Inputs:
    BLDG_ATTR_MAP_DATA = {
        "ORIG":["BID", "location", "BLDG_DED", "BLDG_LIMIT", "BLDG_VALUE", "CNT_DED", "CNT_LIMIT", "CNT_VALUE", "NUM_STORIE", "foundation", "BasementFi", "FIRST_FLOO", "DEMft"],
        "IN":["BID", "location", "BLDG_DED", "BLDG_LIMIT", "BLDG_VALUE", "CNT_DED", "CNT_LIM", "CNT_VALUE", "NUM_STORIE", "foundation", "BasementFi", "FIRST_FLOO", "DEMft"],
        "OUT":["BID", "ORIG_ID", "BLDG_DED", "BLDG_LIM", "BLDG_VAL", "CNT_DED", "CNT_LIM", "CNT_VALUE", "STORY", "FOUND", "BASEFIN", "FFH", "DEMFT"],
        "DESC":["new building id", "source building id", "building deductible", "building limit", "building value", "content deductible", "content limit", "content value", "number of stories", "foundation type", "basement finish type", "first floor height", "ground elevation"],
        "DEF":["-1", "-1", "2000", "200000", "200000", "1000", "100000", "100000", "1", "8", "0", "1", "-9999"],
        "TYPE":['np.int32', 'object', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32', 'np.int32'],
        "CHECK":[0,0,1,1,1,1,1,1,1,1,1,1,1],
        "HDDF":[0,0,0,0,0,0,0,0,1,1,0,1,0],
        "TDDF":[0,0,0,0,0,0,0,0,1,1,1,0,0],
        "ANLYS":[1,0,1,1,1,1,1,1,1,1,1,1,1],
        "DOM":[None, None, None, None, None, None, None, "[1,2,3]", "[2,4,6,7,8,9]", "[0,1,2]", None, None]
    }
    
    GUTS_ATTR_MAP_DATA = {
        "OUT":["BID", "BFD", "DEM", "FFE", "FFEe", "TWL", "TWLe", "BFDe", "RP", "PVAL", "SWEL", "SWELe", "WET", "Hc", "Hce", "PWL1", "PW13", "PWG3", "DDFfam", "ddf2", "ddf3", "ddf4", "DAMLw", "DAMPr", "DAMUp", "BVAL", "rLOSSLw", "rLOSSBE", "rLOSSUp", "Loss_Lw", "Loss_BE", "Loss_Up"],
        "MIN":[1 for i in range(13)] + [0 for i in range(19)],
        "DESC":["building id", "bldg flood depth", "dem elev", "first floor elev", "FFE error", "total water elev", "TWL error", "BFD error", "retrun period", "probability", "stillwater elev", "SWEL error", "ground wet?", "conditonal wave height", "Hc error", "probability wave < 1ft", "probability wave 1-3ft", "probability wave >= 3ft", "cpfra ddf family", "damage for df2", "damage for df3", "damage for df4", "combined min damage", "combined med damage", "combined max damage", "building value", "raw min loss", "raw best estimate loss", "raw max loss", "adjusted min loss", "adjusted best estimate loss", "adjusted max loss"]
    }
    
    def __init__(self, blabber=True, use_heatmap=True, hm_bandwidth=1100, hm_resolution=500, hm_name="heatmap",
        mc_n=2000, nbounds=tuple([0.0001, 1]), storm_csv='', bldg_path='', bldg_lay=None,
        swel_mpath='', swel_path='', swelA_path='', swelB_path='', waveA_path='', waveB_path='', use_uncertainty=True,
        use_cutoff=True, use_cutoff10=False, use_eWet=True, use_waves=True, use_twl=False, use_wavecut50=False, use_erosion=False,
        use_singleloss=False, use_insurance=False, use_contents=False, use_netcdf=False, use_outcsv=False, bddf_lut_path='',
        bldg_ddf_lut=None, cddf_lut_path=None, cont_ddf_lut=None, proj_prefix='', out_shp_path='', blabfile='',
        GCB_fid='', GCB_Bded='', GCB_Blim='', GCB_Bval='', GCB_Cded='', GCB_Clim='', GCB_Cval='', GCB_Bsto='', GCB_Bfou='',
        GCB_Bbfi='', GCB_Bffh='', GCB_Bdem='') -> object:
        
        self.blabber = blabber
        self.use_heatmap = use_heatmap
        self.hm_bandwidth = hm_bandwidth
        self.hm_resolution = hm_resolution
        self.hm_name = hm_name
        self.mc_n = mc_n
        self.nbounds = nbounds
        
        self.storm_csv = storm_csv
        self._use_stormsuite = use_stormsuite
        
        self.bldg_path = bldg_path
        self.bldg_lay = bldg_lay
        
        self.swel_mpath = swel_mpath
        self.swel_path = swel_path
        self.swelA_path = swelA_path
        self.swelB_path = swelB_path
        self.waveA_path = waveA_path
        self.waveB_path = waveB_path
        
        self.use_uncertainty = use_uncertainty
        self.use_cutoff = use_cutoff
        self.use_cutoff10 = use_cutoff10
        self.use_eWet = use_eWet
        self.use_waves = use_waves
        self.use_twl = use_twl
        self.use_wavecut50 = use_wavecut50
        self.use_erosion = use_erosion
        self.use_singleloss = use_singleloss
        self.use_insurance = use_insurance
        self.use_contents = use_contents
        self.use_netcdf = use_netcdf
        self.use_outcsv = use_outcsv
        
        self._bddf_lut_path = _bddf_lut_path
        self.bldg_ddf_lut = bldg_ddf_lut
        
        self.cddf_lut_path = cddf_lut_path
        self.cont_ddf_lut = cont_ddf_lut
        
        self.proj_prefix = proj_prefix
        self.out_shp_path = out_shp_path
        self._blabfile = blabfile
        
        self.bldg_attr_map = pd.Dataframe.from_dict(self.BLDG_ATTR_MAP_DATA)
        self.bldg_attr_map.index = list(range(len(bldg_attr_map.shape[0]))) # to make sure the row index has labels
        
        self.guts_attr_map = pd.Dataframe.from_dict(self.GUTS_ATTR_MAP_DATA)
        
        self._GCB_fid = GCB_fid
        self._GCB_Bded = GCB_Bded
        self._GCB_Blim = GCB_Blim
        self._GCB_Bval = GCB_Bval
        self._GCB_Cded = GCB_Cded
        self._GCB_Clim = GCB_Clim
        self._GCB_Cval = GCB_Cval
        self._GCB_Bsto = GCB_Bsto
        self._GCB_Bfou = GCB_Bfou
        self._GCB_Bbfi = GCB_Bbfi
        self._GCB_Bffh = GCB_Bffh
        self._GCB_Bdem = GCB_Bdem
    
    @property
    def use_stormsuite(self) -> bool:
        if self.storm_csv:
            return True
        else:
            return False
    
    @property
    def bddf_lut_path(self) -> str:
        return self._bddf_lut_path
    
    @bddf_lut_path.setter
    def bddf_lut_path(self, val: str) -> None:
        self._bddf_lut_path = val
        
        if '.csv' in val and os.path.exists(val):
            self.bldg_ddf_lut = pd.read_csv(val)
    
    @property
    def blabfile(self) -> str:
        if self.out_shp_path and self.proj_prefix:
            return os.path.join(self.out_shp_path, f'{self.proj_prefix}_run.log')
        else:
            return ''
    
    @property
    def GCB_fid(self) -> str:
        return self._GCB_fid
    
    @GCB_fid.setter
    def GCB_fid(self, val: str) -> None:
        self._GCB_fid = val
        self.bldg_attr_map.loc[1,"IN"] = val
    
    @property
    def GCB_Bded(self) -> str:
        return self._GCB_Bded
    
    @GCB_Bded.setter
    def GCB_Bded(self, val: str):
        self._GCB_Bded = val
        self.bldg_attr_map.loc[2,"IN"] = val
    
    @property
    def GCB_Blim(self) -> str:
        return self._GCB_Blim
    
    @GCB_Blim.setter
    def GCB_Blim(self, val: str) -> None:
        self._GCB_Blim = val
        self.bldg_attr_map.loc[3,"IN"] = val
    
    @property
    def GCB_Bval(self) -> str:
        return self._GCB_Bval
    
    @GCB_Bval.setter
    def GCB_Bval(self, val: str) -> None:
        self._GCB_Bval = val
        self.bldg_attr_map.loc[4,"IN"] = val
    
    @property
    def GCB_Cded(self) -> str:
        return self._GCB_Cded
    
    @GCB_Cded.setter
    def GCB_Cded(self, val: str) -> None:
        self._GCB_Cded = val
        self.bldg_attr_map.loc[5,"IN"] = val
    
    @property
    def GCB_Clim(self) -> str:
        return self._GCB_Clim
    
    @GCB_Clim.setter
    def GCB_Clim(self, val: str) -> None:
        self._GCB_Clim = val
        self.bldg_attr_map.loc[6,"IN"] = val
    
    @property
    def GCB_Cval(self) -> str:
        return self._GCB_Cval
    
    @GCB_Cval.setter
    def GCB_Cval(self, val: str) -> None:
        self._GCB_Cval = val
        self.bldg_attr_map.loc[7,"IN"] = val
    
    @property
    def GCB_Bsto(self) -> str:
        return self._GCB_Bsto
    
    @GCB_Bsto.setter
    def GCB_Bsto(self, val: str) -> None:
        self._GCB_Bsto = val
        self.bldg_attr_map.loc[8,"IN"] = val
    
    @property
    def GCB_Bfou(self) -> str:
        return self._GCB_Bfou
    
    @GCB_Bfou.setter
    def GCB_Bfou(self, val: str) -> None:
        self._GCB_Bfou = val
        self.bldg_attr_map.loc[9,"IN"] = val
    
    @property
    def GCB_Bbfi(self) -> str:
        return self._GCB_Bbfi
    
    @GCB_Bbfi.setter
    def GCB_Bbfi(self, val: str) -> None:
        self._GCB_Bbfi = val
        self.bldg_attr_map.loc[10,"IN"] = val
    
    @property
    def GCB_Bffh(self) -> str:
        return self._GCB_Bffh
    
    @GCB_Bffh.setter
    def GCB_Bffh(self, val: str) -> None:
        self.GCB_Bffh = val
        self.bldg_attr_map.loc[11,"IN"] = val
    
    @property
    def GCB_Bdem(self) -> str:
        return self._GCB_Bdem
    
    @GCB_Bdem.setter
    def GCB_Bdem(self, val: str) -> None:
        self.GCB_Bdem = val
        self.bldg_attr_map.loc[12,"IN"] = val


class PFRACoastal:
    def __init__(self) -> object:
        pass
    
    def runPFRACoastal(inputs: Inputs) -> None:
        pass