# Building Inventories

To facilitate consequence analysis, the package anticipates users to bring one of three types of structure
inventories: National Structure Inventory (NSI) data, Milliman data, or a user-defined (custom) 
data source. Whichever inventory type is provided, several required fields are needed to perform 
loss calculations. However, the tool's aim is to require as little data pre-processing as possible. 
Several strategies are employed to facilitate a seemless user experience:

- Auto-detection of required fields by checking against a variety of field naming conventions
- Auto-population of missing values for fields with default values
- Ability to provide user-overrides for NSI and Milliman data field names
- Documentation for all inventory sources, including custom dataset requirements
- Validation of user inputs against a defined schema


## Base Buildings Class

TODO: Insert definitions of a base buildings schema for performing consequence analysis for 
inland and coastal application. "Target_fields' referenced below should be defined here.  

## NSI Data

TODO: Insert definitions of NSI buildings schema.
![NSI Example](images/nsi.jpg)

## Milliman Data

Milliman was tasked by FEMA to support the Risk Rating 2.0 initiative. Part of this effort was to 
develop a Market Basket of structures. Three separate books (portfolios of policies) were created from 
the Market Basket data: 

1. Uniform Book  
2. Uncorrelated Market Basket  
3. Correlated Market Basket  

Users should refer to FEMA for further details on the Milliman datasets: [Link](https://www.fema.gov/sites/default/files/documents/FEMA_Risk-Rating-2.0_Methodology-and-Data-Appendix__01-22.pdf)

Currently, the tool is configured to accept either Uniform Book or Uncorrelated Market Basket data as 
inputs for consequence analysis. The expected schema of Milliman data is provided below for reference.

*Milliman Data Schema:*
```json
{%
   include "schemas/milliman_schema.json"
%}
```
However, users may provide a crosswalk (a.k.a. override) from the target fields to the user's non-standard
fields.

*Example of User-Provided Override for Milliman Field Names:*  
(keys=target_field, values=user's field)
```json
{
    "building_cost": "my_custom_building_cost_field"
}
```
 *Milliman GIS Data:*
<!-- <img src="images/milliman-uniform.jpg" alt="Milliman Uniform Book Example" width="500"> -->
![Milliman Uniform Book Example](images/milliman-uniform.jpg)

## User Defined Data

TODO: Insert definitions a user-defined buildings dataset. Seems this should reflect the base class.