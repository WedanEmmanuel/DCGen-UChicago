from .IT_configuration import DatacenterITConfiguration
from .Cooling_Power_Infrastructures import DatacenterNonITConfiguration
from pydantic import BaseModel, model_validator, Field
from pydantic.errors import PydanticUserError
from typing import Union, List
import os
from pathlib import Path
import math
import json
import pandas as pd
from typing import ClassVar, Dict, Any
import re


datacenter_use_cases = ["AI training", "AI inference", "Mixed AI training and inference", "Cloud"]
heat_rejection_modes = ["Dry cooling", "Evaporative cooling"]
SINGLE_GPU_TDP =0.7 #kW H200 

class inputs(BaseModel):
    datacenter_use_case: str
    datacenter_scale    : dict
    specific_datacenters: Union[str, List[str]] 
    non_IT_design_optimization_criterion : Union[str, List[str]]
    rack_per_row : int = Field(gt=0) # > 0 
    safety_margin: float = Field(ge=0) # >= 0 
    rows_per_pod: int= Field(gt=0) # > 0 
    Heat_rejection_mode: str
    Redundancy: dict 


    DEFAULT_FIELDS: ClassVar[Dict[str, Any]] = {
            "rack_per_row": 10,
            "rows_per_pod": 2,
            "safety_margin": 0,
            "Heat_rejection_mode": "Dry cooling",
            "Redundancy": 
                { "Heat Rejection":  "N+1", 
                    "Chillers" : "N+1", 
                    "CDUs" :  "N+1", 
                    "PDUs" :  "N+1",
                    "UPSs" :  "2N", 
                    "MSBs" : "2N",
                    "Backup Generators" : "2N"
                }, 
            "non_IT_design_optimization_criterion" : ["Space"], #, "power"],   
            "specific_datacenters": ["2024 Canonical Configuration"],
            "specific_non_IT_hardware" : "All"
        }
    
    @model_validator(mode="before")
    @classmethod
    def add_missing_defaults(cls, values):
        

        for key, default in cls.DEFAULT_FIELDS.items():
            if key not in values or values[key] is None:
                values[key] = default

        return values
    
    # List of required fields with no defaults
    REQUIRED_FIELDS : ClassVar[Dict[str, Any]] = {
        "datacenter_use_case" : datacenter_use_cases ,
        "datacenter_scale" : [{'target' : "'power_capacity'" , 
                                'capacity': "str  (e.g., '1GW')" },
                              {'target' : "'rack_count'", 
                                'capacity': "Int  (e.g., 1000)"  },
                              {'target' : "'gpu_count'", 
                                'capacity': "Int  (e.g., 1000)"  },
                              {'target' : "'gpu_power'", 
                                'capacity': "str  (e.g., 100 MW)"  }                          
                             ]
    }

    @model_validator(mode="before")
    @classmethod
    def validate_required_fields(cls, values):
        errors = []

        #  Check missing required fields
        for key,field in cls.REQUIRED_FIELDS.items():
            if key not in values or values[key] is None:
                possible_values = "\n".join([f"'{key}': '{item}'" for item in field])
                errors.append({
                    "loc": key,
                    "msg": f"Missing required field '{key}'.\nPossible definitions inlude :\n{possible_values}",
                    "type": "missing_field"
                })

        #  Type-check required fields
        
        for key,field in cls.REQUIRED_FIELDS.items():
            if key in values:
                expected_type = cls.model_fields[key].annotation
                if not isinstance(value := values[key], expected_type):
                    possible_values = "\n".join([f"'{key}': '{item}'" for item in field])
                    errors.append({
                        "loc": key,
                        "msg": f"Incorrect type for '{key}'. Expected {expected_type}, got {type(value)}. \nPossible definitions include:\n"
                        f"{possible_values}",
                        "type": "type_error"
                    })

        # If any errors collected, raise combined Pydantic error
        if errors:
            #Convert each dict to a string before joining
            error_strings = [f"{e['msg']}" for e in errors]
            raise PydanticUserError("\n".join(error_strings),code="custom_validation_error")

        return values





    
ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

it_configuration_obj = DatacenterITConfiguration()

non_it_hardware_obj = DatacenterNonITConfiguration()
latest_configuration={}
last_input={}


"""A function to display all the datacenter IT configs supported for a given model """
def get_available_it_configurations_list(datacenter_use_case="AI training") :

    if not datacenter_use_case in datacenter_use_cases :
        raise ValueError(f"Incorrect datacenter use case. Please provide a value in {datacenter_use_cases}")
    
    it_configuration_obj.UseReferenceHardwareModel(datacenter_use_case)

    """if any(word in model.lower() for word in  ["reference", "ref"]):   
        it_configuration_obj.UseReferenceHardwareModel(datacenter_use_case)
    elif any(word in model.lower() for word in  ["canonical", "canonic"]):   #by default
        it_configuration_obj.UseCanonicalHardwareModel(datacenter_use_case)  #USE ONLY CANONICAL CONFIGURATIONS
    else:
        raise ValueError("Incorrect model type specified. Please provide a value in ['Canonical model', 'Reference model']")
    """
    
    return it_configuration_obj.getDatacentersList()



"""A function to display all the datacenter cooling configs supported for a given heat rejection mode"""
def get_available_cooling_system_hardware_list(Heat_rejection_mode= ["Dry cooling", "Evaporative cooling"]) :
    cooling_configs = {}

    if isinstance(Heat_rejection_mode, str):
        if Heat_rejection_mode.lower()=="all" :
            Heat_rejection_mode = heat_rejection_modes 
        else :
            Heat_rejection_mode = [Heat_rejection_mode]

    for heatsink in Heat_rejection_mode :
        if heatsink.lower() in [x.lower() for x in ['dry', 'dry cooling', "drycooling", 'dry_cooling', 'dry-cooling']]:
            non_it_hardware_obj.use_dry_cooling()
        elif heatsink.lower() in [x.lower() for x in ['evaporative', 'cooling tower', 'evaporative cooling', "evaporativecooling", 'evaporative_cooling', 'evaporative-cooling']]:
            non_it_hardware_obj.use_evaporative_cooling()
        else : 
            raise ValueError("Heat rejection mode undesupported. Define 'Heat_rejection_mode' in the list ['Dry cooling', 'Evaporative cooling']")

        cooling_configs = cooling_configs | non_it_hardware_obj.get_available_hardware(["Heat Rejection"])

        
    Hardware_types = ["Chillers", 'CDUs']  
    cooling_configs =  cooling_configs | non_it_hardware_obj.get_available_hardware(Hardware_types)

    return  json.dumps(cooling_configs, ensure_ascii=False, indent=4)   



"""A function to display all the datacenter cooling and power distribution configs supported for a given heat rejection mode"""
def get_available_power_system_hardware_list( ) :
    Hardware_types = ["PDUs", 'UPSs','MSBs', "Backup Generators"]
    return  json.dumps(non_it_hardware_obj.get_available_hardware(Hardware_types), ensure_ascii=False, indent=4)   



"""A function to display the latest datacenter IT configs generated"""
def get_datacenter_it_configurations() :
    it_config={}
    for datacenter_name,datacenter_config in latest_configuration.items() : 
        it_config[datacenter_name] = datacenter_config["IT configuration"]
    return json.dumps({"IT configuration": it_config}, ensure_ascii=False, indent=4)


"""A function to display the latest datacenter cooling  configs generated"""
def get_cooling_system_configurations() :
    cooling_system_configs={}
    for datacenter_name,datacenter_config in latest_configuration.items() : 
        cooling_system_configs[datacenter_name] = datacenter_config["Cooling system"]
    
    return json.dumps({"Cooling System": cooling_system_configs}, ensure_ascii=False, indent=4)

def get_summary_cooling_system_configurations() :
    cooling_system_configs={}
    for datacenter_name,datacenter_config in latest_configuration.items() : 
        cooling_system_configs[datacenter_name] = datacenter_config["Cooling system"]["Summary"]
    
    return json.dumps({"Cooling System": cooling_system_configs}, ensure_ascii=False, indent=4)



"""A function to display the latest datacenter power distribution configs generated"""
def get_power_distribution_system_configurations() :
    Power_system_configs={}
    for datacenter_name,datacenter_config in latest_configuration.items() : 
        Power_system_configs[datacenter_name] = datacenter_config["Power system"]
    return json.dumps({"Power Distribution System": Power_system_configs}, ensure_ascii=False, indent=4)
   

"""A function to display the latest datacenter power distribution configs generated"""
def get_summary_power_distribution_system_configurations() :
    Power_system_configs={}
    for datacenter_name,datacenter_config in latest_configuration.items() : 
        Power_system_configs[datacenter_name] = datacenter_config["Power system"]["Summary"]
    return json.dumps( {"Power Distribution System": Power_system_configs}, ensure_ascii=False, indent=4)
   


#Function to generate cooling and power distribution configs to serve a certain datacenter
def configure_gray_space_hardware(ITConfig, input_params):
    input_params = inputs(**input_params)

    if input_params.Heat_rejection_mode.lower() in [x.lower() for x in ['dry', 'dry cooling', "drycooling", 'dry_cooling', 'dry-cooling']]:
        non_it_hardware_obj.use_dry_cooling()
    elif input_params.Heat_rejection_mode.lower() in [x.lower() for x in ['evaporative', 'cooling tower', 'evaporative cooling', "evaporativecooling", 'evaporative_cooling', 'evaporative-cooling']]:
        non_it_hardware_obj.use_evaporative_cooling()
    else : 
        raise ValueError("Heat rejection mode undesupported. Define heat ''Heat_rejection_mode'' in the list ['Dry cooling', 'Evaporative cooling']")
        
    
    if hasattr(input_params, "Redundancy"):
        non_it_hardware_obj.update_redundancy(input_params.Redundancy)


    non_it_hardware_obj.updataITConfigurations(
            ITConfig,
            SafeTyMargin=input_params.safety_margin,
            RacksPerRow=input_params.rack_per_row,
            rows_per_pod=input_params.rows_per_pod
        )
    
    if isinstance(input_params.non_IT_design_optimization_criterion, str):
        input_params.non_IT_design_optimization_criterion = [input_params.non_IT_design_optimization_criterion]

    if hasattr(input_params, "Redundancy") or  not  isinstance(input_params.specific_non_it_hardware_list, dict) : 
        specific_non_it_hardware_list = "All" 
    else :
        specific_non_it_hardware_list = non_it_hardware_obj.format_specific_non_it_hardware(input_params.specific_non_it_hardware_list, input_params.non_IT_design_optimization_criterion)
    
    for criterium in input_params.non_IT_design_optimization_criterion :
        if 'space' == criterium.lower() :
            non_it_hardware_obj.ComputeDatacenterSpaceEfficientCoolingAndPowerSystems(specificHardwareList=specific_non_it_hardware_list)
        if 'power' == criterium.lower() : 
            non_it_hardware_obj.ComputeDatacenterPowerEfficientCoolingAndPowerSystems(specificHardwareList=specific_non_it_hardware_list)
    return non_it_hardware_obj.getNonITConfigurations() 
        



def load_input_data(input_data: Union[str, dict]) -> dict:
    """
    Accepts:
    - JSON file path (str)
    - JSON string (str)
    - Python dictionary

    Returns:
    - Python dictionary

    Raises:
    - ValueError with clear message if input is invalid
    """

    # -----------------------------
    # Case 1: Already a dictionary
    # -----------------------------
    if isinstance(input_data, dict):
        return input_data

    # -----------------------------
    # Case 2: A string, file path or JSON text?
    # -----------------------------
    if isinstance(input_data, str):

        # Treat as file path if it exists
        path = Path(input_data)
        if path.exists() and path.is_file():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError as e:
                raise ValueError(f"File '{input_data}' contains invalid JSON: {e}")

        # Otherwise treat as JSON string
        try:
            return json.loads(input_data)
        except json.JSONDecodeError:
            raise ValueError(
                "Input is neither a valid JSON string nor a valid JSON file path."
            )

    # -----------------------------
    # Case 3: Everything else, error
    # -----------------------------
    raise ValueError("Input must be a JSON file path, JSON string, or dict.")



def configure_target_datacenter(input_params ) : 

    input_params_ = load_input_data(input_params) 
    input_params = inputs(**input_params_)

    
    """keywords = ["reference", "ref"]
    if any(word in input_params.model.lower() for word in keywords):   
        it_configuration_obj.UseReferenceHardwareModel()
    else :   #by default
        it_configuration_obj.UseCanonicalHardwareModel()   #USE ONLY CANONICAL CONFIGURATIONS
    """

    it_configuration_obj.UseReferenceHardwareModel()

    if  all(ch == "-" for ch in input_params.specific_datacenters) or  all(ch == " " for ch in input_params.specific_datacenters) : 
        input_params.specific_datacenters = "All"

    if isinstance(input_params.specific_datacenters, str) and input_params.specific_datacenters.lower() != 'all':
        input_params.specific_datacenters = [input_params.specific_datacenters]

    if not "datacenter_scale" in input_params_.keys() or not 'target' in input_params.datacenter_scale.keys() :
        raise ValueError("Target datacenter specifications incorrect: please provide 'datacenter_scale'    :{ 'target' : } in the list [power_capacity, rack_count]")
         
    
    elif input_params.datacenter_scale['target'] == 'rack_count':
        if  not('capacity' in input_params.datacenter_scale.keys() or isinstance(input_params.datacenter_scale['capacity'], Union[float, int])):
            raise ValueError("Target datacenter specifications incorrect: please provide 'datacenter_scale'    :{ 'capacity' : } as a number of racks in the target datacenter")
            
        if not isinstance(input_params.datacenter_scale['capacity'], int) :
            print(f"You want to configure a datacenter with {input_params.datacenter_scale['capacity']} racks. Rounding to {math.ceil(input_params.datacenter_scale['capacity'])} ")
            input_params.datacenter_scale['capacity'] = math.ceil(input_params.datacenter_scale['capacity'])

        it_configuration_obj.updateDatacenterHardwareConfig(input_params.datacenter_use_case, input_params.datacenter_scale['capacity'], input_params.specific_datacenters)
    
    elif input_params.datacenter_scale['target'] == 'gpu_count':
            it_configuration_obj.configure_datacenter_it_with_gpu_power(input_params.datacenter_use_case, str(input_params.datacenter_scale['capacity']*SINGLE_GPU_TDP) + 'kW', input_params.specific_datacenters )

    elif input_params.datacenter_scale['target'] == 'power_capacity':
        if  not ('capacity' in input_params.datacenter_scale.keys() or isinstance(input_params.datacenter_scale['capacity'], str)):
            raise ValueError("Target datacenter specifications incorrect: please provide 'datacenter_scale'    :{ 'capacity' : } as target datacenter capacity (e.g. 1MW, 1GW, 100kW ...)")
        it_configuration_obj.updateDatacenterTargetPowerCapacity(input_params.datacenter_use_case, input_params.datacenter_scale['capacity'], input_params.specific_datacenters)
    
    elif input_params.datacenter_scale['target'] == 'gpu_power':
        it_configuration_obj.configure_datacenter_it_with_gpu_power(input_params.datacenter_use_case, str(input_params.datacenter_scale['capacity']), input_params.specific_datacenters )
    
    else : 
        raise ValueError("Target datacenter specifications incorrect: please provide 'datacenter_scale'  :{ 'target' :,  'capacity':}")

    datacenters_config = {}
    global last_input
    last_input = input_params_ 
    datacenters_list =  it_configuration_obj.getDatacenterConfigData().keys()

    for i, datacenter in enumerate(datacenters_list, start=1):
        ITConfig = it_configuration_obj.getDatacenterConfigData()[datacenter]

        gray_space_hardware_config = configure_gray_space_hardware(ITConfig, input_params_)
        if len(datacenters_list) > 1 :
          datacenters_config[f"Datacenter {i} (" + datacenter + ")"] = {"IT configuration": ITConfig} | gray_space_hardware_config
        else :
          datacenters_config[f"Datacenter (" + datacenter + ")"] = {"IT configuration": ITConfig} | gray_space_hardware_config

    global latest_configuration
    latest_configuration = datacenters_config
   
    return  json.dumps(datacenters_config, ensure_ascii=False, indent=4)


def save_datacenter_configuration(datacenters_config,filepath='Output-Configurations/Config', single_file=True):
    
    # --- Convert JSON string to dict if necessary ---
    if isinstance(datacenters_config, str):
        try:
            datacenters_config = json.loads(datacenters_config)
        except json.JSONDecodeError:
            raise ValueError("Input string is not valid JSON.")
    
    if not isinstance(datacenters_config, dict):
        raise TypeError("datacenters_config must be a dict or JSON string.")
    
    # Split filepath into base + ext
    base, ext = os.path.splitext(filepath)    

    file_dir =os.path.dirname(filepath)
    if not os.path.isdir(file_dir):
        raise FileNotFoundError(f"File path {file_dir} not found")

    if single_file :
        
        expected_ext = ".json"

        if ext.lower() != expected_ext:
            # If no extension or incorrect extension, replace with correct one
            filepath = base + expected_ext

        
        with open(filepath, "w") as f:
            json.dump(datacenters_config, f, ensure_ascii=False, indent=4)
        print(f"Datacenter configuration saved to {filepath}")

    else : 
        for config_name,config_data in datacenters_config.items() : 
            #extract datacenter name if there is for instance "Configuration x (name)"
            match = re.search(r'\((.*?)\)', config_name)
            if match:
                name = match.group(1).replace(' ', '_')
            else:
                name = config_name.replace(' ', '_')    # or '' or some default
                        
            global last_input
            if last_input['datacenter_scale']["target"] =='rack_count':
                filepath = file_dir +  '/' + last_input['datacenter_use_case'].replace(' ', '_') + '_' + name + '_' + str(last_input['datacenter_scale']['capacity']).replace(' ', '_') + '_racks.json'
            else:
                filepath = file_dir + '/' + last_input['datacenter_use_case'].replace(' ', '_') + '_' + name + '_' + last_input['datacenter_scale']['capacity'].replace(' ', '_') + '.json'
            with open(filepath, "w") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            print(f"Datacenter [{config_name}]  saved to {filepath}")
    



# Expose only the public functions
__all__ = [ "get_available_it_configurations_list",
            'get_available_cooling_system_hardware_list',
            'get_available_power_system_hardware_list',
            "configure_target_datacenter",
            "get_datacenter_it_configurations",
            "get_cooling_system_configurations",
            "get_power_distribution_system_configurations", 
            "get_summary_cooling_system_configurations",
            "get_summary_power_distribution_system_configurations", 
            "save_datacenter_configuration"
          ]