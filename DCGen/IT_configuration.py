import json
import math
import statistics
import re


#The data is organized in json files "ITConfigFile". whith the following structure
'''
 "Configuration" :
    {
       "RackSize": ,  (RU)
       "RackType" : "Cloud", (Or HPC)
       "NodeTypes":
        {
            "CPU":  (or GPU or CPU-GPU depending on the datacenter type)
            {
                "Rackcount": ,   (Number of racks)
                "RackTDP":       (Peak power demand of each rack)
            },
            "Storage": (or CPU or CPU-GPU depending on the datacenter type)
            {
                "Rackcount": , (Number of racks)
                "RackTDP" :     (Peak power demand of each rack)
            }
        },
        "floorSpace": ,    (m^2/rack or sqft/rack)
        "Generation" :  (deployement year)
    }
'''


class DatacenterITConfiguration:
    def __init__(self, dataCenterType = 'AI training', NumberOfRacksInDatacenter=1000):

        self.hardwareConfigModel="Canonical"
        self.dataCenterType = dataCenterType
        self.hardwareConfigFilesDir ="./IT_hardware_config/"
        self.HardwareConfigFiles = {'Canonical':
                                        {
                                            "AI training": "TrainingDatacenters.json",
                                            "AI inference": "InferenceDatacenters.json",
                                            "Mixed AI training and inference": "MixTrainInferenceDatacenters.json",
                                            "Mixed AI training \n and inference": "MixTrainInferenceDatacenters.json",
                                            "Cloud" : "CloudDatacenters.json"
                                        },
                                      'Reference': 
                                        {
                                            "AI training": "TrainingSystems.json",
                                            "AI inference": "InferenceSystems.json",
                                            "Mixed AI training and inference": "MixTrainInferenceSystems.json",
                                            "Mixed AI training \n and inference": "MixTrainInferenceSystems.json",
                                            "Cloud" : "CloudSystems.json"
                                        }
                                    }
                                

        self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]


        #Path of json file containing baseline/reference datacenter configurations.
                                            #E.g., this may be AITraining.json, CloudDatacenters.json...
                                            #with several reference datacenters in the file. The files parameters/keys
                                            # are described above



        self.NumberOfRacksInDatacenter = NumberOfRacksInDatacenter  #Number of racks the user wiches to build
        self.TargetDatacenterPowerCapacity = 0  #Target power capacity in MW.
        self.DatacentersList = []         # A variable with the list of datacenters in the config file
        self.datacenterConfigData = {}    # A dictionary with the model output. This may also be changed to be a csv file that save the data, with little effort

        self.ConventionlRackSize = 42
        
        self.HPCToCloudRackRatio = 2/3



        self.storage_node_tdp_for_ai_nodes = 0.708 #kW
        self.storage_node_tdp_for_cloud_nodes = 0.438 #kW
        self.storage_rack_unit = 1

    def UseCanonicalHardwareModel(self, datacenterType="AI training" ):
      self.hardwareConfigModel = "Canonical"
      self.dataCenterType      = datacenterType
      self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]


    def UseReferenceHardwareModel(self,datacenterType ="AI training"):
      self.hardwareConfigModel = "Reference"
      self.dataCenterType      = datacenterType
      self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]



    def updateConfigName(self, OldConfigName, NewConfigName) -> dict :
      if not self.datacenterConfigData:
        print("No data center configuration generated")
        return {}
      else :
        self.datacenterConfigData[NewConfigName] = self.datacenterConfigData.pop(OldConfigName)
        return self.datacenterConfigData


    #This function estimates the number of external storage racks required when the following parameters are given:
    #The datacenter's storage capacity in Terabytes, The the storage capacity of each node (TB), storage and rack size in (rack units),

    def estimateStorageConfigFromStorCapacity(self,DataCenterStorageCapacityTB, StorageNodeCapacityTB,StorageNodeRU,RackCapacityRU, StorageNodeTDP) -> dict :
        storageNodesCount = math.ceil(DataCenterStorageCapacityTB/StorageNodeCapacityTB)
        storageNodesPerRack = round(RackCapacityRU/StorageNodeRU)
        storageRackCount = math.ceil(storageNodesCount/storageNodesPerRack)
        return {"Storage": {"Rackcount": storageRackCount, "RackTDP": StorageNodeTDP * storageNodesPerRack}}


    #This function estimates the number of external storage racks required when the following parameters are given:
    #Power consumed by the compute racks, storage and rack size in (rack units), proportion of power attributable to storage
    #From xAI COLOSSUS estimation, we set a the default proportion to 4.2%
    def estimateStorageConfigFromPowerProportion(self,ComputeracksPower,StorageNodeRU,RackCapacityRU, StorageNodeTDP, DataCenterStorageProportion=0.042) -> dict :
        StoragePower = DataCenterStorageProportion * ComputeracksPower/(1-DataCenterStorageProportion)
        storageNodescount = math.ceil(StoragePower/StorageNodeTDP)
        storageNodesPerRack = round(RackCapacityRU/StorageNodeRU)

        storageRackCount = math.ceil(storageNodescount/storageNodesPerRack)
        return {"Storage": {"Rackcount": storageRackCount, "RackTDP": StorageNodeTDP * storageNodesPerRack}}


    #This function estimates the number of external storage racks required when the following parameters are given:
    #datacenter compute capability (TFLOPS), DiskIOPS (Input/Output Operations per second), the number of disks per node,
    #storage and rack size in (rack units), and a target ratio between the datacenter external storage IOPS and compute capability (TFLOPS)
    # In the Microsoft NCCads_H100_v5 sizes series, each Nvidia H100 GPU (94GB) (of 1,979TFLOPS) can use up to 8x100,000 IOPS disks. That is a ratio of 404 IOPS/TFLOPS
    def estimateStorageConfigFromIOPSandTFLOPS(self, DCTFLOPS, DiskIOPS,NumberDiskPerNode, StorageNodeRU, RackCapacityRU, StorageNodeTDP, IOPSPerTFLOPS=404) -> dict :
        StorgeNodesCount = math.ceil(DCTFLOPS * IOPSPerTFLOPS/(DiskIOPS * NumberDiskPerNode))
        storageNodesPerRack = round(RackCapacityRU/StorageNodeRU)

        storageRackCount = math.ceil(StorgeNodesCount / storageNodesPerRack)
        return {"Storage": {"Rackcount": storageRackCount, "RackTDP": StorageNodeTDP * storageNodesPerRack}}


    def getDatacenterConfigData(self) -> dict :
      return self.datacenterConfigData

    #A function that allow to check all the datacenters listed in the json file This may be usefull to
    # if the user only wants to work with a particular datacenter out of all the configurations in the file.
    def getDatacentersList(self):
      try:
        with open(self.ITConfigFile, 'r') as file:
            datacenters =json.load(file)
            self.DatacentersList = list(datacenters.keys())
            #print(self.DatacentersLis)
            return self.DatacentersList
      except FileNotFoundError:
        print(f"The file at {self.ITConfigFile} was not found.")
      except json.JSONDecodeError:
        print(f"The file at {self.ITConfigFile} is not valid JSON.")
      except Exception as e:
        print(f"An error occurred: {e}")

    #this function computes the desired datacenter power capacity, power density
    """
    Output dictionary (self.datacenterConfigData):
    {
    'datacenter name': {
                      'Peak power': {'node type 1 (e.g. GPU)': xxx, 'noode type 2 (e.g. Storage)': xxx},
                      'Rack count': {'node type 1 (e.g. GPU)': xxx, 'noode type 2 (e.g. Storage)': xxx},
                      'Power density': xxx,
                      'Space Utilization': xxx,
                      'Generation': 'xxx'
                    }
    }"""

    def generatedCanonicalConfig(self, datacenterType='AI training',Year="All") -> dict : 
      # parse the data from json files for the two types of node racks
      self.UseReferenceHardwareModel(datacenterType)
      data ={}
      try:
        with open(self.ITConfigFile , 'r') as file:
            data =json.load(file)
        
        if Year == "All":
          if not data:
            print(f"No data found in {self.ITConfigFile }")
            return {}
          SpecificDataCenters = list(data.keys())

        else: 
          SpecificDataCenters = [item for item in data if data[item]["Generation"] == Year]

        # contains the canonical 
        Result = {
                    "RackSize"   : self.ConventionlRackSize ,  
                    "RackType"   : "Cloud", 
                    "floorSpace" :  statistics.mean([data[item]["floorSpace"] for item in SpecificDataCenters]) ,  
                    "Generation" :  max([data[item]["Generation"] for item in SpecificDataCenters])
                }


        RacksConfig = data[SpecificDataCenters[0]]["NodeTypes"]
        Result['NodeTypes'] = RacksConfig 

        
        for NodeType in RacksConfig.keys():

          Result["NodeTypes"][NodeType]["Rackcount"] = sum([data[item]["NodeTypes"][NodeType]["Rackcount"] for item in SpecificDataCenters])
          Result["NodeTypes"][NodeType]["RackTDP"]   =  sum([data[item]["NodeTypes"][NodeType]["RackTDP"] *self.ConventionlRackSize/ data[item]["RackSize"]  for item in SpecificDataCenters if data[item]["RackType"]=="Cloud"])
          Result["NodeTypes"][NodeType]["RackTDP"]   += sum([data[item]["NodeTypes"][NodeType]["RackTDP"] * self.HPCToCloudRackRatio * self.ConventionlRackSize/ data[item]["RackSize"]  for item in SpecificDataCenters if data[item]["RackType"]=="HPC"])

          non_zero_count = sum( [data[item]["NodeTypes"][NodeType]["Rackcount"] != 0 for item in SpecificDataCenters ])
          if non_zero_count > 0:
            Result["NodeTypes"][NodeType]["RackTDP"] = round(Result["NodeTypes"][NodeType]["RackTDP"]/non_zero_count, 1)
          else:
            Result["NodeTypes"][NodeType]["RackTDP"] = 0
            
        return Result 

      except FileNotFoundError:
        print(f"The file at {self.ITConfigFile } was not found.")
      except json.JSONDecodeError:
        print(f"The file at {self.ITConfigFile } is not valid JSON.")
      except Exception as e:
        print(f"An error occurred while reading config file: {e}")
        print(self.ITConfigFile )

    def generateAITrainingCanonicalConfig(self, ComputeRackCount={'GPU': 100}) :
      config =  self.generatedCanonicalConfig(datacenterType='AI training',Year="2024")

      NodeTypeFound = ''
      for NodeType in list(config["NodeTypes"].keys()):
          if NodeType in ComputeRackCount:
            rackType1Ref = config["NodeTypes"][NodeType]["Rackcount"] 
            NodeTypeFound = NodeType
            config["NodeTypes"][NodeType]["Rackcount"] = ComputeRackCount[NodeType]
          else :
            config["NodeTypes"][NodeType]["Rackcount"] =  math.ceil(config["NodeTypes"][NodeType]["Rackcount"] * ComputeRackCount[NodeTypeFound]/rackType1Ref)
      
      return config

    def generateCloudCanonicalConfig(self, ComputeRackCount={'CPU': 100}) :
      config =  self.generatedCanonicalConfig(datacenterType='Cloud',Year="2024")
      NodeTypeFound = ''
      for NodeType in list(config["NodeTypes"].keys()):
          if NodeType in ComputeRackCount:
            rackType1Ref = config["NodeTypes"][NodeType]["Rackcount"] 
            NodeTypeFound = NodeType
            config["NodeTypes"][NodeType]["Rackcount"] = ComputeRackCount[NodeType]
          else :
            config["NodeTypes"][NodeType]["Rackcount"] =  math.ceil(config["NodeTypes"][NodeType]["Rackcount"] * ComputeRackCount[NodeTypeFound]/rackType1Ref)
      return config



    def generateAIInferenceCanonicalConfig(self, ComputeRackCount={'CPU-GPU': 100, 'CPU': 100}) :
      configCPU_GPU =  self.generatedCanonicalConfig(datacenterType='AI inference',Year="2024")
      configCPU =  self.generatedCanonicalConfig(datacenterType='Cloud',Year="2024")
      
      for config in [configCPU_GPU, configCPU]:
        NodeTypeFound = ''
        for NodeType in list(config["NodeTypes"].keys()):
            if NodeType in ComputeRackCount:
              rackType1Ref = config["NodeTypes"][NodeType]["Rackcount"] 
              NodeTypeFound = NodeType
              config["NodeTypes"][NodeType]["Rackcount"] = ComputeRackCount[NodeType]
            else :
              config["NodeTypes"][NodeType]["Rackcount"] =  math.ceil(config["NodeTypes"][NodeType]["Rackcount"] * ComputeRackCount[NodeTypeFound]/rackType1Ref)

      for key, value in configCPU["NodeTypes"].items():
        if key in configCPU_GPU["NodeTypes"]:
          configCPU_GPU["NodeTypes"][key]["Rackcount"] += configCPU["NodeTypes"][key]["Rackcount"]
          configCPU_GPU["NodeTypes"][key]["RackTDP"]   = max([configCPU["NodeTypes"][key]["RackTDP"], configCPU_GPU["NodeTypes"][key]["RackTDP"]])
        else:
          configCPU_GPU["NodeTypes"][key] = value
      return configCPU_GPU

    def generateMixedAITrainingInferenceCanonicalConfig(self, ComputeRackCount={'GPU': 100, 'CPU-GPU': 100}) :
      
      configGPU =  self.generatedCanonicalConfig(datacenterType='AI training',Year="2024")
      configCPU_GPU =  self.generatedCanonicalConfig(datacenterType='AI inference',Year="2024")
      
      for config in [configGPU, configCPU_GPU]:
        NodeTypeFound = ''
        for NodeType in list(config["NodeTypes"].keys()):
            if NodeType in ComputeRackCount:
              rackType1Ref = config["NodeTypes"][NodeType]["Rackcount"] 
              NodeTypeFound = NodeType
              config["NodeTypes"][NodeType]["Rackcount"] = ComputeRackCount[NodeType]
            else :
              config["NodeTypes"][NodeType]["Rackcount"] =  math.ceil(config["NodeTypes"][NodeType]["Rackcount"] * ComputeRackCount[NodeTypeFound]/rackType1Ref)

      for key, value in configCPU_GPU["NodeTypes"].items():
        if key in configGPU["NodeTypes"]:
          configGPU["NodeTypes"][key]["Rackcount"] += configCPU_GPU["NodeTypes"][key]["Rackcount"]
          configGPU["NodeTypes"][key]["RackTDP"]   = max([configGPU["NodeTypes"][key]["RackTDP"], configCPU_GPU["NodeTypes"][key]["RackTDP"]])
        else:
          configGPU["NodeTypes"][key] = value
      return configGPU



    def __buildDatacenterWithRackConfig(self, SpecificDataCenters="All") :
      # parse the data from json files for the two types of node racks
      data ={}
      try:
        with open(self.ITConfigFile , 'r') as file:
            data =json.load(file)

        Result = {}

        if SpecificDataCenters == "All":
          if not data:
            print(f"No data found in {self.ITConfigFile }")
            return {}
          SpecificDataCenters = data.keys()


        for DCconfig in SpecificDataCenters:
            if DCconfig not in data.keys():
              print(f"No data found for {DCconfig} in {self.ITConfigFile }")
              return {}

            PowerDensity = 0
            PeakPower = 0
            Rack1Count = 0
            RacksConfig = data[DCconfig]["NodeTypes"]
            Result[DCconfig] = {}

            for NodeType in RacksConfig.keys():
              Rack1Count += round(RacksConfig[NodeType]['Rackcount'])

            totalRacks = 0
            for NodeType in RacksConfig.keys():
              RackCount = round(self.NumberOfRacksInDatacenter * RacksConfig[NodeType]['Rackcount']/Rack1Count )
              totalRacks +=RackCount
              RacksConfig[NodeType]['Rackcount'] = RackCount

            #To make sure errors of rounding does not lead to excess racks than the target
            if(totalRacks > self.NumberOfRacksInDatacenter):
              RacksConfig[NodeType]['Rackcount'] -= (totalRacks - self.NumberOfRacksInDatacenter)
            if(totalRacks < self.NumberOfRacksInDatacenter):
              RacksConfig[NodeType]['Rackcount'] += (-totalRacks + self.NumberOfRacksInDatacenter)

            #RacksConfig[list(RacksConfig.keys())[0]]['Rackcount'] = Rack1Count
            #RacksConfig[list(RacksConfig.keys())[1]]['Rackcount'] = self.NumberOfRacksInDatacenter - Rack1Count
            Result[DCconfig]["Peak power (MW)"] = {}
            Result[DCconfig]["Rack count"] = {}

            for NodeType in RacksConfig.keys():
              Result[DCconfig]["Rack count"][NodeType] = RacksConfig[NodeType]['Rackcount']

              if data[DCconfig]['RackType'] == 'HPC' :
                Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.HPCToCloudRackRatio * self.ConventionlRackSize * RacksConfig[NodeType]['Rackcount']  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"] ), 3)
                PowerDensity +=  RacksConfig[NodeType]['Rackcount']  * self.HPCToCloudRackRatio * self.ConventionlRackSize*  RacksConfig[NodeType]['RackTDP'] /(data[DCconfig]["floorSpace"] * self.NumberOfRacksInDatacenter *  data[DCconfig]["RackSize"]  )
              else :
                Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.ConventionlRackSize * RacksConfig[NodeType]['Rackcount']  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"]), 3 )
                PowerDensity +=    self.ConventionlRackSize * RacksConfig[NodeType]['Rackcount']   *  RacksConfig[NodeType]['RackTDP'] /( data[DCconfig]["RackSize"] * data[DCconfig]["floorSpace"] * self.NumberOfRacksInDatacenter )

            Result[DCconfig]['Power density (kW/m²)'] = round( PowerDensity, 3)
            Result[DCconfig]['Space Utilization (m²)'] = round(self.NumberOfRacksInDatacenter * data[DCconfig]["floorSpace"],1)
            Result[DCconfig]['Hardware Generation'] = data[DCconfig]['Generation']

        self.datacenterConfigData = Result

      except FileNotFoundError:
        print(f"The file at {self.ITConfigFile } was not found.")
      except json.JSONDecodeError:
        print(f"The file at {self.ITConfigFile } is not valid JSON.")
      except Exception as e:
        print(f"An error occurred: {e}")
        print(self.ITConfigFile )



    #A function allowing to change datacenter configuration at runtime with no need to create a new class.
    # eg. change the number of racks, the config file
    def updateDatacenterHardwareConfig(self, datacenterType, NumberOfRacksInDatacenter, SpecificDataCenters="All"):
      self.dataCenterType = datacenterType
      self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]

      self.NumberOfRacksInDatacenter = NumberOfRacksInDatacenter

      if self.NumberOfRacksInDatacenter <= 0:
        raise ValueError(
            f"The number of racks in the target datacenter must be a positive non zero value. ({self.NumberOfRacksInDatacenter} found)"
        )
      

      self.__buildDatacenterWithRackConfig(SpecificDataCenters)


    def convert_to_kw(self,power_str):
      """
      Convert a string like '1MW' or '500W' to kilowatts (kW).
      Supports units: W, kW, MW, GW
      """
      units = {'W': 1e-3, 'KW': 1, 'MW': 1e3, 'GW': 1e6, 'TW':1e9}

      # Separate number and unit
      """num_part = ''.join(filter(lambda c: c.isdigit() or c == '.', power_str.upper()))
      unit_part = ''.join(filter(str.isalpha, power_str.upper()))

      if unit_part not in units:
          raise ValueError(f"Unsupported unit: {unit_part}    {unit_part}")
      
      return float(num_part) * units[unit_part]"""

      power_str_ = power_str.strip().upper()

      match = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)\s*(W|KW|MW|GW|TW)', power_str_)
      if not match:
          raise ValueError(f"Invalid power format: '{power_str_}'")

      value = float(match.group(1))
      unit = match.group(2)

      if value <= 0:
          raise ValueError(f"target power. Power value must be positive (found {power_str_})")

      return value * units[unit]



    #Instead, this function allows to estimate the hardware configurations based on a target power capacity
    # and a specific reference configuration in the json file
    def buildDatacenterWithPowerCapacity(self, TargePowerCapacity = '1GW', SpecificDataCenters="All") :
      data ={}
      try:
        with open(self.ITConfigFile , 'r') as file:
            data =json.load(file)
        Result = {}

        if SpecificDataCenters == "All":

          if not data:
            print(f"No data found in {self.ITConfigFile }")

            return {}
          SpecificDataCenters = data.keys()

        PeakPower = self.convert_to_kw(TargePowerCapacity)


        self.TargetDatacenterPowerCapacity = PeakPower/1e3


        for DCconfig in SpecificDataCenters:
            if DCconfig not in data.keys():
              print(f"No data found for {DCconfig} in {self.ITConfigFile }")
              return {}

            PowerDensity = 0
            RackCount = 0
            RacksConfig = data[DCconfig]["NodeTypes"]
            Result[DCconfig] = {}

            for NodeType in RacksConfig.keys():
              RackCount += round(RacksConfig[NodeType]['Rackcount'])
              if data[DCconfig]['RackType'] == 'HPC' :
                PowerDensity +=  RacksConfig[NodeType]['Rackcount']  * self.HPCToCloudRackRatio * self.ConventionlRackSize*  RacksConfig[NodeType]['RackTDP'] /(data[DCconfig]["floorSpace"] *  data[DCconfig]["RackSize"]  )
              else:
                PowerDensity +=  RacksConfig[NodeType]['Rackcount']   * self.ConventionlRackSize*  RacksConfig[NodeType]['RackTDP'] /(data[DCconfig]["floorSpace"] * data[DCconfig]["RackSize"]  )

            PowerDensity = PowerDensity/RackCount
            self.NumberOfRacksInDatacenter = round(PeakPower/(PowerDensity* data[DCconfig]["floorSpace"]))

            for k in range(len(list(RacksConfig.keys()))):
              RackCount_ = round(self.NumberOfRacksInDatacenter * RacksConfig[list(RacksConfig.keys())[k]]['Rackcount']/RackCount )
              RacksConfig[list(RacksConfig.keys())[k]]['Rackcount'] = RackCount_

            #RackCount = round(self.NumberOfRacksInDatacenter * RacksConfig[list(RacksConfig.keys())[0]]['Rackcount']/RackCount )
            #RacksConfig[list(RacksConfig.keys())[0]]['Rackcount'] = RackCount
            #RacksConfig[list(RacksConfig.keys())[1]]['Rackcount'] = self.NumberOfRacksInDatacenter - RackCount
            Result[DCconfig]["Peak power (MW)"] = {}
            Result[DCconfig]["Rack count"] = {}

            for NodeType in RacksConfig.keys():
              Result[DCconfig]["Rack count"][NodeType] = RacksConfig[NodeType]['Rackcount']

              if data[DCconfig]['RackType'] == 'HPC' :
                Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.HPCToCloudRackRatio * self.ConventionlRackSize * RacksConfig[NodeType]['Rackcount']  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"] ),3)
              else :
                Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.ConventionlRackSize * RacksConfig[NodeType]['Rackcount']  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"]), 3 )

            Result[DCconfig]['Power density (kW/m²)'] =  round(PowerDensity,3)
            Result[DCconfig]['Space Utilization (m²)'] = round(PeakPower/PowerDensity,1)
            Result[DCconfig]['Hardware Generation'] = data[DCconfig]['Generation']
          
        self.datacenterConfigData = Result

      except FileNotFoundError:
        print(f"The file at {self.ITConfigFile } was not found.")
      except json.JSONDecodeError:
        print(f"The file at {self.ITConfigFile } is not valid JSON.")
      except Exception as e:
        print(f"An error occurred wile reading {e}")



    #A function allowing to change datacenter configuration at runtime with no need to create a new class.
    # eg. change the number of racks, the config file
    def updateDatacenterTargetPowerCapacity(self, datacenterType, PowCapacity, SpecificDataCenters='All'):
        self.dataCenterType = datacenterType
        self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]

        self.buildDatacenterWithPowerCapacity(PowCapacity, SpecificDataCenters)



    def configure_datacenter_it_with_gpu_power(self, datacenterType,total_gpu_power, SpecificDataCenters="All"):
      self.dataCenterType = datacenterType
      self.ITConfigFile =   self.hardwareConfigFilesDir + self.hardwareConfigModel + self.HardwareConfigFiles[self.hardwareConfigModel][self.dataCenterType]

      data ={}
      try:
        with open(self.ITConfigFile , 'r') as file:
            data =json.load(file)
        Result = {}

        if SpecificDataCenters == "All":

          if not data:
            print(f"No data found in {self.ITConfigFile }")

            return {}
          SpecificDataCenters = data.keys()


        gpu_power = self.convert_to_kw(total_gpu_power)
        

        for DCconfig in SpecificDataCenters:
            if DCconfig not in data.keys():
              print(f"No data found for {DCconfig} in {self.ITConfigFile }")
              return {}


            RacksConfig = data[DCconfig]["NodeTypes"]
            Result[DCconfig] = {}
            Result[DCconfig]["Peak power (MW)"] = {}
            Result[DCconfig]["Rack count"] = {}

            total_racks = 0
            total_compute_power = 0

            if "GPU" in RacksConfig.keys() :
              gpu_node_label = 'GPU'
            elif "CPU-GPU" in RacksConfig.keys():
                gpu_node_label = 'CPU-GPU'
            else:
              raise ValueError(
                              f" {datacenterType} dacencenter does not use GPUs "
                          )
            
            gpu_racks = math.ceil(gpu_power/RacksConfig[gpu_node_label]['RackTDP'])
            
            for NodeType in RacksConfig.keys():
              if gpu_node_label=="Storage":
                continue

              Result[DCconfig]["Rack count"][NodeType] = gpu_racks

              if data[DCconfig]['RackType'] == 'HPC' :
                  Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.HPCToCloudRackRatio * self.ConventionlRackSize * Result[DCconfig]["Rack count"][NodeType] *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"] ),3)
              else :
                Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.ConventionlRackSize * Result[DCconfig]["Rack count"][NodeType]  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"]), 3 )
              total_racks += Result[DCconfig]["Rack count"][NodeType] 
              total_compute_power += Result[DCconfig]["Peak power (MW)"][NodeType] * 1e3
            
            storage_config = self.estimateStorageConfigFromPowerProportion(total_compute_power,self.storage_rack_unit, 
                                                                        self.ConventionlRackSize , self.storage_node_tdp_for_ai_nodes, DataCenterStorageProportion=0.042) 
            NodeType = 'Storage'
            Result[DCconfig]["Rack count"][NodeType] = storage_config['Storage']['Rackcount']
            RacksConfig[NodeType]['RackTDP'] = storage_config['Storage']['RackTDP']
            Result[DCconfig]["Peak power (MW)"][NodeType] = round(self.ConventionlRackSize * Result[DCconfig]["Rack count"][NodeType]  *  RacksConfig[NodeType]['RackTDP']/(1e3 * data[DCconfig]["RackSize"]), 3 )

            total_racks += Result[DCconfig]["Rack count"][NodeType] 
            total_compute_power += Result[DCconfig]["Peak power (MW)"][NodeType] * 1e3


            Result[DCconfig]['Power density (kW/m²)'] =  round(total_compute_power/(total_racks * data[DCconfig]["floorSpace"]),3)
            Result[DCconfig]['Space Utilization (m²)'] = round(total_racks * data[DCconfig]["floorSpace"],1)
            Result[DCconfig]['Hardware Generation'] = data[DCconfig]['Generation']
          
        self.datacenterConfigData = Result

      except FileNotFoundError:
        print(f"The file at {self.ITConfigFile } was not found.")
      except json.JSONDecodeError:
        print(f"The file at {self.ITConfigFile } is not valid JSON.")
      except Exception as e:
        print(f"An error occurred wile reading {e}")
    
        
        
