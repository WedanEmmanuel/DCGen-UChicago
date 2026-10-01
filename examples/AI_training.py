from DCGen import *
import json
import os



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PARAMETERS_DIR = BASE_DIR + '/Inputs/input_reference_AI_training.json'


try:
    with open(INPUT_PARAMETERS_DIR, "r") as f :
        input_parameters =  json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(f"File '{INPUT_PARAMETERS_DIR}' contains invalid JSON: {e}")

"""print('-------- AVAILABLE IT CONFIGURATIONS --------')
print(get_available_it_configurations_list(input_parameters['datacenter_use_case']) )
"""

"""print()
print('-------- AVAILABLE COOLING SYSTEMS --------')

print(get_available_cooling_system_hardware_list())
"""


"""print('-------- AVAILABLE IT MODELS --------')
print(get_available_it_configurations_list(input_parameters['datacenter_use_case']) )
"""



print('-------- GENERATE DATACENTER CONFIGURATIONS  --------')

DATACENTER_CONFIG = configure_target_datacenter(INPUT_PARAMETERS_DIR)

#print('-------- SHOW DETAILED DATACENTER CONFIGURATION (IT, COOLING, POWER SYSTEM)  --------')
#print(config)


print('-------- SHOW ONLY IT CONFIGURATIONS --------')

print(get_datacenter_it_configurations())


"""print('-------- SHOW DETAILED COOLING SYSTEM --------')

print(get_cooling_system_configurations())"""



print('-------- SHOW A SUMMARY OF THE COOLING SYSTEM --------')

print(get_summary_cooling_system_configurations())


"""print('-------- SHOW DETAILED POWER DISTRIBUTION SYSTEM --------')

print(get_power_distribution_system_configurations())
"""


print('-------- SHOW A SUMMARY OF THE POWER DISTRIBUTION SYSTEM --------')

print(get_summary_power_distribution_system_configurations())

"""print('-------- SAVE CONFIGURATIONS IN A FILE OF YOUR CHOICE --------')
OUTPUT_DIR = BASE_DIR + "/Output-configurations/"
os.makedirs(OUTPUT_DIR, exist_ok=True)
save_datacenter_configuration(DATACENTER_CONFIG, filepath= OUTPUT_DIR + 'AI_training_10000_racks.json', single_file=True)"""