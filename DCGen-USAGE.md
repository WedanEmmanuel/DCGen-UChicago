

## DCGen Inputs 
This Section describes the input parameters.
They are encoded in JSON files to ease the tool's utilization. 

### Required parameters
  - **datacenter_use_case**: one of four available use cases:  ```"AI training"```      or ```"AI inference"``` or ```"Mixed AI training and inference"```, or ```"Cloud"```. Example of parameter declaration: 
    ```python 
      "datacenter_use_case" : "AI training"
    ```


  - **datacenter_scale**:  specify the target (rack count or power capacity), and the IT capacity (e.g., 1000 racks, 1 GW ....). Example of parameter definition:
    
    ``` python 
        "datacenter_scale":
        { 
          'target' : 'rack_count' or 'power_capacity' #  Generate datacenter with target  number of racks or target IT power capacity
          'capacity' : 1000  or '100MW'    # E.g., 1000 racks in the target datacenter, or the 100 MW  power target if you generate with 'power_capacity'. One can specify multiples of watts (W, kW, MW, GW, TW)   
        }
    ``` 



  - **Heat_rejection_mode**: one of two available heat rejection modes: ```"Dry cooling"``` and  ```"Evaporative cooling"```. Example of the parameter usage:

    ```python 
      "Heat_rejection_mode" : "Dry cooling"
    ```
  
   
  - **rack_per_row**: IT racks are arranged in rows.  Example of racks in a row.:
    ``` python 
      "rack_per_row" : 10
    ```
    The default value used by DCGen is 10.

  
  - **rows_per_pod**: IT rack rows are grouped into pods. For instance, two rows form a pod for cooling and power distribution (aisle-based arrangement). Example of rack rows grouped in a pod: 

    ``` python 
      "rows_per_pod" : 2
    ```
    The default value used by DCGen is 2.

 
  - **safety_margin**: cooling and power distribution capacity overprovisionning to account for future datacenter growth and/or safety. It is a positive number. For instance, specifying a value of 0.2 means that at each level of hierarchy in the cooling and power distribution systems, the equipment is oversized by 20% of the required nominal capacity. Example of parameter declaration:

    ``` python 
      "safety_margin" : 0.2
    ```

 - **Redundancy**:  Two redundancy types: ```N+r``` where ```r``` is positive (e.g., N+1, N+2, ...) and ```xN/y``` where ```x``` and ```y``` are positive (e.g., N, 2N, 4N/3...). ```"Heat Rejection"``` is a common parameter for dry coolers and cooling towers (depending on ```Heat_rejection_mode```).  The following example constitutes the default redundancy setup.

    ``` python
    "Redundancy" :
      { "Heat Rejection":  "N+1", 
          "Chillers" : "N+1", 
          "CDUs" :  "N+1", 
          "PDUs" :  "N+1",
          "UPSs" :  "2N", 
          "MSBs" : "2N",
          "Backup Generators" : "2N"
      }                                  
    ```
  
 - **non_IT_design_optimization_criterion**: one or more optimization objectives:```"Space"```,   or ```"Power"```, or a list with both. Examples of declaration: 
    ``` python 
        "non_IT_design_optimization_criterion" : "Space"
        "non_IT_design_optimization_criterion" : "Power"
        "non_IT_design_optimization_criterion" : ["Power", "Space"]
    ```

    By default, DCGen generates the configurations that  optimize for both power and space. 




### Optional parameters

  - **specific_datacenters**: a list of  reference/canonical IT configuration names. Examples of canonical configuration names include ```"2024 Canonical Configuration", "2027 Canonical Configuration", "2029 Canonical Configuration"```, or ```"All"```. Examples of other reference systems include ```"xAI COLOSSUS", "NVIDIA NVL576",..., "All"```.  One may get the complete list of IT configurations using ```get_available_it_configurations_list(datacenter_use_case) ``` function.  Examples of parameter declaration:

    ``` python 
        specific_datacenters : ["2027 Canonical Configuration", "2029 Canonical Configuration"]
        specific_datacenters : ["xAI COLOSSUS", "NVIDIA NVL576"]
    ```
    
    The default value is ```"All"```, which instructs DCGen to generate all available configurations that match the specified ```datacenter_use_case```.
  
 

  - **specific_non_IT_hardware**: subset of hardware names in the cooling or power distribution systems. If a component is not specified or is defined as ```"All"``` (e.g., ```UPSs: "All"```), DCGen generates the  optimed configuration among all the available hardware options. UPS, MSBs and backup generators  are designed for IT and Facility (i.e, the cooling system). Example of parameter definition:
  
    ```python
      "specific_non_IT_hardware"
        : {'Heat Rejection' : list,  # list of spacific cooling tower/dry cooler, 
          'Chillers': list, # list of the specific chillers names to use in the design
          'CDUs': list ,
          'PDUs': list ,
          'UPSs': { 'IT': list, 'Facility': list}, 
          'MSBs':  {'IT': list, 'Facility': list}, 
          'Backup generators': {'IT': list, 'Facility': list}  
        }   
    ```
    One can get the complete list of cooling hardware  using ```get_available_cooling_system_hardware_list()``` function. Similarly, the hardware available at each level of the power distribution hierarchy can be obtained using this function: ```get_available_power_system_hardware_list()```.



## DCGen Functions
- ```configure_target_datacenter(input_parameter)```: configures the target datacenter with the inputs specified. The user may provide```input_parameter``` as one of these: (1) a JSON file path containing the input data structure, (2) a JSON string, or (3) a python  dictionary.  

- ```get_available_it_configurations_list(datacenter_use_case="AI training")```: retrieves the supported IT configurations for a given datacenter use case.

- ```get_available_cooling_system_hardware_list(Heat_rejection_mode= ["Dry cooling", "Evaporative cooling"])```: retrieves the supported cooling hardware. ```Heat_rejection_mode``` is one of :```"Dry cooling"```, ```"Evaporative cooling"```,  or a list containing both, or ```"All"```. The output is a list of all cooling system components (CDUs, Chillers, and Dry coolers/Evaporative cooling towers). 


- ```get_available_power_system_hardware_list()```: returns the list of power distribution hardware available in DCGen (Backup generators, UPSs, MSBs, PDUs).


- ```get_cooling_system_configurations()```: retrieves the latest cooling system configurations generated. 

- ```get_power_distribution_system_configurations()```: retrieves the latest power distribution configurations generated. 


 - ```save_datacenter_configuration(datacenters_config,filepath=Output-Configurations/Config.json, single_file=True)```: saves a given configuration as json file. The user provides the configuration (e.g., output of ```configure_target_datacenter()``` function) and a filepath (directory of the file to save).  Setting ```single_file``` to ```True``` means that all datacenter configurations are stored in a single file. Otherwise, each configuration is saved in a separate file within the directory specified in ```filepath```, with filenames matching the configuration name (e.g., ```AI_training_2024_Canonical_Datacenter_1GW.json```, ```AI_inference_2029_Canonical_Datacenter_1000_racks.json```)



# DCGen Outputs 
- ```configure_target_datacenter(input_parameter)```: produces a json string (output datacenter configuration) with the following structure :

```python
    {
    'datacenter model name ': 
      'IT' :
        {
          'Peak power (MW)': 
          {
            'node type 1 (e.g. GPU)': float,
            'node type 2 (e.g. Storage)': float,
            ...
          }, 
          'Rack count': 
          {
            'node type 1 (e.g. GPU)': float,
            'node type 2 (e.g. Storage)': float,
             ...
            },
          'Power density (kW/m²)': float,   
          'Space Utilization (m²)': float,
          'Hardware Generation': int     # 2024, 2027, 2029
        },
      'Cooling system':
        {  
            'Dry Coolers': 
              {'Space Optimized Design': 
                {
                  'IT': 
                    {
                      'Name': str,  #Hardware name
                      'Total hardware count': int ,  # Number of components involved in the design
                      'Total Capacity (MW)': float,  #Total cooling capacity in MWth thermal
                      'Space Utilization (m²)': float,  #Space Utilization of Dry Coolers component in m²
                      'Space Efficiency': float, # Amount of Cooling (kWth) delivered per unit of space used (m²) 
                      'Maximum power demand': float, # Maximum power demand of the Dry coolers
                      'Power Efficiency': float  # Amount of cooling (kWth) delivered  per kWe of electricity consumed
                    }
                }, 
                'Power Optimized Design': 
                  {
                      #Same structure as in space optimized. This is only applicable if "Power" is specified as optimization criterium
                  },
            },
                        
            "Chiller" : {...}, #Same structure and so on for  CDUs


            "Summary":  #Summary of the cooling system
            {
              "Power Optimized Design": {
                'Maximum power demand (MW)': float #Maximum power demand of the cooling system (MWe)
                'Space Utilization (m²)' :  #Total space use by the cooling system (m²) 
                {
                  "In datacenter Floor" : float 
                    "Outside": float
                }
              }, 

              "Space Optimized Design": 
              {
                'Maximum power demand (MW)': float #Maximum power demand of the cooling system (MWe)
                'Space Utilization (m²)' :  #Total space use by the cooling system (m²) 
                {
                  "In datacenter Floor" : float 
                    "Outside": float
                }
              }
            }
      }, 
      "Power system" : 
      {
        'UPSs': 
          {'Space Optimized Design': 
            {
              'IT': 
              {
                'Name': str,  #Hardware name
                'Total hardware count': int ,  # Number of components involved in the design
                'Total Capacity (MW)': float,  #Total UPS capacity  (MWe)
                'Space Utilization (m²)': float,  #Space Utilization of the UPSs component (m²)
                'Space Efficiency (kW/m²)': float, #Amount of power delivered (kWe) per unit of space used (m²) 
                'Maximum Conversion Power (MW)': float, # Power loss in conversion (MW)
                'Power Efficiency': float  # Power efficiency  in the range [0-1] as specifyed by the manufacturer
              }, 
              'Facility': 
              {
                'Name': str,  #Hardware name
                'Total Hardware count': int ,  #Number of components involved in the design
                'Total Capacity (MW)': float,  #Total UPSs capacity in MWe
                'Space Utilization (m²)': float,  #Space Utilization of the UPSs component (m²)
                'Space Efficiency (kW/m²)': float, #Amount of power delivered (kWe) per unit of space used (m²) 
                'Maximum Conversion Power (MW)': float, # Power loss in conversion (MWe)
                'Power Efficiency': float  # Power efficiency  in the range [0-1] as specifyed by the manufacturer
              }
            }, 

            'Power Optimized Design': 
            {
                #Same structure as in space optimized. This is only applicable if "Power" is specified as input
            },
          },

        "MSBs" : {...} # Same structure
        "Summary":  #Summary of the power distribution system
        {
          "Space Optimized Design" :
          {
            'Maximum Conversion Power (MW)': float #Maximum Conversion Power in the power distribution system (MW)
            'Space Utilization (m2)' :  #Total space requirements (m²) 
            {
                "In datacenter Floor" : float 
                "Outside": float
            }
          } , 

          "Power Optimized Design" :
          {
            'Maximum Conversion Power (MW)': float #Maximum Conversion Power in the power distribution system (MW)
            'Space Utilization (m2)' :  #Total space requirements (m²) 
            {
                "In datacenter Floor" : float 
                "Outside": float
            }
          } 
        }
      }   
    }
 ```


- ```get_available_it_configurations_list(datacenter_use_case)```: produces a list of configurations supported for a given datacenter type. Example for AI training:

  ```python 
    ['2024 Canonical Configuration', '2027 Canonical Configuration', '2029 Canonical Configuration', 'Frontier', 'Aurora Argonne', 'xAI COLOSSUS', 'DGX SuperPOD', 'EL CAPITAN', 'NVIDIA NVL576']
  ```


- ```get_available_cooling_system_hardware_list(Heat_rejection_mode= ["Dry cooling", "Evaporative cooling"])``` and ```get_available_power_system_hardware_list()```:  produce  JSON strings with lists of hardware as follows:

  ```python 
    {
      "Dry coolers": list,
      "Evaporative Cooling Towers": list,
      "Chillers": list,
      "CDUs": list
    }
  ```

- ```get_cooling_system_configurations()``` and ```get_power_distribution_system_configurations()``` produce JSON strings of cooling and power distribution systems respectively. The output structure is the following : 
  ```python 
    {
      "2024 Canonical Configuration" :
      {
        'Dry cooler': list,  #Names of all dry coolers
        'Chillers': list, #
        ... #So on for all the hardware types
      }, 

      '2027 Canonical Configuration': 
      {
        ...
      }, 
      ...
    }
  ```


Examples of the tool use are provided in [Examples](./examples/) folder.

