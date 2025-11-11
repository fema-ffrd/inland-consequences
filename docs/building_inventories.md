# Building Inventories Technical Implementation

To facilitate consequence analysis, the **Consequences Solution** is designed to accept one of three types of structure inventories:

1. **National Structures Inventory (NSI)**
1. **Milliman Market Basket Data**
1. **User-defined (custom) data sources**

Whichever inventory type is provided, several **required fields** are needed to perform loss calculations.\
However, the Consequences Solution’s design minimizes the need for extensive data preprocessing.\
Several strategies are implemented to facilitate a seamless user experience:

- **Auto-detection** of required fields by checking against a variety of field naming conventions
- **Auto-population** of missing values for fields with default values
- **User-overrides** for NSI and Milliman data field names
- **Comprehensive documentation** for all inventory sources, including custom dataset requirements
- **Validation** of user inputs against a defined schema

## Base Buildings Class

TODO: Insert definitions of a base buildings schema for performing consequence analysis for
inland and coastal application. "Target_fields' referenced below should be defined here.

## NSI Data

TODO: Insert definitions of NSI buildings schema.
![NSI Example](images/nsi.jpg)

## Milliman Market Basksets Data

The following describes technical details related to the implementation of **Milliman Market Basket** data and schema.\
For more information on the analytical use of these datasets, refer to the [**Inventory Methodology Documentation**](inventory_milliman.md).

Currently, the **Consquences Solution** supports **Uniform Book** and **Uncorrelated Market Basket** data as inputs for consequence analysis.\
The expected schema of Milliman data is provided below for reference.

### *Milliman Data Schema:*

```json
{%
   include "schemas/milliman_schema.json"
%}
```

However, users may provide a crosswalk (a.k.a. override) from the target fields to the user's non-standard
fields.

*Example of User-Provided Override for Milliman Field Names:*\
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
