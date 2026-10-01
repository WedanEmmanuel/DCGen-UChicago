import json
import math
import pandas as pd
import re
from enum import Enum
#The data is organized in json files "ConfigFile". whith the following structure
#1. For Cooling system
'''
  name" :
    {
       "Capacity"   (kW)
       "PeakPowerConsumption" (kW)
       "Dimensions":
        {
            "Height"  (m)
            "Width" (m)
            "Depth" (m)
        },
        "AccessAreaShare" (e.g., 0.2 (for 20%))
        "Generation" :  (deployement year)
    }
'''
#2. For Power system
'''
 "name" :
    {
       "Capacity"   (kW)
       "Efficiency" (in [0-1]. E.g. 0.997 for 99.7%)
       "Dimensions":
        {
            "Height"  (m)
            "Width" (m)
            "Depth" (m)
        },
        "AccessAreaShare" (e.g., 0.2 (for 20%))
        "Generation" :  (deployement year)
    }
'''

class DatacenterNonITConfiguration:

    class DesignLevel(Enum):
      DatacenterLevel = "Datacenter"
      RowLevel = "Row"
    
    class Systems(Enum):
      CoolingSystem = "Cooling system"
      PowerSystem  = "Power system"

    class RedundancySetups(Enum):
      N_plus_r = "N+r"
      x_N_over_y = "xN/y"

    class ITvsFacilityDesignPhase(Enum):
      IT = 'IT'
      Facility = "Facility"

    class equipmentTypes(Enum):
      CoolingTowers = "Evaporative Cooling Towers"
      DryCoolers = "Dry coolers"
      Chillers = "Chillers"
      CDUs = "CDUs"
      MSBs = "MSBs"
      Generators = "Backup Generators"
      PDUs = "PDUs"
      UPSs = "UPSs"
      
    class EfficiencyArbitrage(Enum):
      SpaceEfficientDesign = "Space Optimized Design" 
      PowerEfficientDesign = "Power Optimized Design"

    class HardwareLocation(Enum):
      Indoors = ['Chillers', "CDUs", "MSBs", "PDUs", 'UPSs']
      Outdoors = ['Evaporative Cooling Towers', "Dry coolers","Backup Generators" ]

    def __init__(self, It_config={}, SafeTyMargin = 0.2, RacksPerRow = 10, rows_per_pod=2):
      
      if It_config :
        dataCenterScalekW = sum(It_config['Peak power (MW)'][RackType] * 1e3 for RackType in It_config['Peak power (MW)'])
      else:
         dataCenterScalekW = 1000 

      self.dataCenterScalekW = self.convert_to_kw(dataCenterScalekW)
      self.it_config = It_config 
      self.RacksPerRow = RacksPerRow
      self.rows_per_pod = rows_per_pod
      self.SafeTyMargin = SafeTyMargin
      self.hardwareConfigFilesDir ="./Non_IT_hardware_config/"

      self.DesignStep = self.ITvsFacilityDesignPhase.IT.value
      self.NonITHardwareConfig = {}
      self.HardwareDesigns     = {}
      self.EfficientDesigns    = {}
      self.using_dry_cooling = False
      self.Redundancy_configs = { "Heat Rejection":  "N+1", 
                                  "Chillers" : "N+1", 
                                  "CDUs" :  "N+1", 
                                  "PDUs" :  "N+1",
                                  "UPSs" :  "2N", 
                                  "MSBs" : "2N",
                                  "Backup Generators" : "2N"
                                 }
      self.__clearData() 
      
       


      
    def __clearData(self):
        self.NonITHardwareConfig ={}
        
        self.HardwareDesigns = {
                                  self.Systems.CoolingSystem.value:
                                  {
                                    #self.equipmentTypes.CoolingTowers.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: "N+1"}  ,"ConfigFile" :"CoolingTowers.json"},
                                    #self.equipmentTypes.DryCoolers.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: "N+1"}  ,"ConfigFile" :"DryCoolers.json"},
                                    self.equipmentTypes.Chillers.value: {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['Chillers']} ,"ConfigFile" :"WaterCooledChillers.json"},
                                    self.equipmentTypes.CDUs.value: {"Design level": self.DesignLevel.RowLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['CDUs']} ,"ConfigFile" :"CoolantDistributionUnits.json"},
                                  },
                                  
                                  self.Systems.PowerSystem.value:
                                  {
                                    self.equipmentTypes.PDUs.value: {"Design level": self.DesignLevel.RowLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['PDUs']} ,"ConfigFile" :"PowerDistributionUnits.json"},
                                    self.equipmentTypes.UPSs.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['UPSs'], self.ITvsFacilityDesignPhase.Facility.value: self.Redundancy_configs['UPSs']} ,"ConfigFile" :"UninterruptiblePowerSupply.json"},
                                    self.equipmentTypes.MSBs.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['MSBs'], self.ITvsFacilityDesignPhase.Facility.value: self.Redundancy_configs['MSBs']} ,"ConfigFile" :"MainSwitchBoards.json"},
                                    self.equipmentTypes.Generators.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['Backup Generators'], self.ITvsFacilityDesignPhase.Facility.value: self.Redundancy_configs['Backup Generators']} ,"ConfigFile" :"Generators.json"}
                                  }
                                }

        self.EfficientDesigns =  {
                                    self.Systems.CoolingSystem.value:
                                    {
                                      #self.equipmentTypes.CoolingTowers.value: { },
                                      #self.equipmentTypes.DryCoolers.value: { },
                                      self.equipmentTypes.Chillers.value: { },
                                      self.equipmentTypes.CDUs.value: {},
                                      "Summary" : {}
                                    },
                                    self.Systems.PowerSystem.value:
                                    {
                                      self.equipmentTypes.PDUs.value: { },
                                      self.equipmentTypes.UPSs.value : { },
                                      self.equipmentTypes.MSBs.value: {},
                                      self.equipmentTypes.Generators.value: { },
                                      "Summary" : { }
                                    }
                                }   # Contains the best configurations we estimated.
        
        if self.using_dry_cooling : 
          self.HardwareDesigns[self.Systems.CoolingSystem.value].pop(self.equipmentTypes.CoolingTowers.value , None)   # removes key if exists, does nothing otherwise
          self.EfficientDesigns[self.Systems.CoolingSystem.value].pop(self.equipmentTypes.CoolingTowers.value , None)   # removes key if exists, does nothing otherwise

          self.HardwareDesigns[self.Systems.CoolingSystem.value] = {self.equipmentTypes.DryCoolers.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value: self.Redundancy_configs['Heat Rejection']}  ,"ConfigFile" :"DryCoolers.json"}} | self.HardwareDesigns[self.Systems.CoolingSystem.value] 
          self.EfficientDesigns[self.Systems.CoolingSystem.value] = {self.equipmentTypes.DryCoolers.value: {}} | self.EfficientDesigns[self.Systems.CoolingSystem.value]
        else:   
          self.HardwareDesigns[self.Systems.CoolingSystem.value].pop(self.equipmentTypes.DryCoolers.value , None)   # removes key if exists, does nothing otherwise
          self.EfficientDesigns[self.Systems.CoolingSystem.value].pop(self.equipmentTypes.DryCoolers.value , None)   # removes key if exists, does nothing otherwise

          self.HardwareDesigns[self.Systems.CoolingSystem.value] = {self.equipmentTypes.CoolingTowers.value : {"Design level": self.DesignLevel.DatacenterLevel.value, "Redundancy":{self.ITvsFacilityDesignPhase.IT.value:self.Redundancy_configs['Heat Rejection'] }  ,"ConfigFile" :"CoolingTowers.json"} } | self.HardwareDesigns[self.Systems.CoolingSystem.value]
          self.EfficientDesigns[self.Systems.CoolingSystem.value] = {self.equipmentTypes.CoolingTowers.value : {}} | self.EfficientDesigns[self.Systems.CoolingSystem.value]


    def use_evaporative_cooling(self) :
      self.using_dry_cooling = False
      self.__clearData()

    def use_dry_cooling(self) :
      self.using_dry_cooling = True
      self.__clearData()

    def update_redundancy(self, RedancancParams = { "Heat Rejection":  "N+1", 
                                  "Chillers" : "N+1", 
                                  "CDUs" :  "N+1", 
                                  "PDUs" :  "N+1",
                                  "UPSs" :  "2N", 
                                  "MSBs" : "2N",
                                  "Backup Generators" : "2N"
                                 }) : 
       
       for key, value in RedancancParams.items() :
          if key not in self.Redundancy_configs : 
            print(f"Equipment {key} unknown. The exhastive list of parameters is {[self.Redundancy_configs.keys()]}")
            return
          self.Redundancy_configs[key] = value


    def updataITConfigurations(self, it_config, SafeTyMargin=0.2, RacksPerRow = 10, rows_per_pod=2):

      self.it_config = it_config 
      self.dataCenterScalekW = sum(it_config['Peak power (MW)'][RackType] * 1e3 for RackType in it_config['Peak power (MW)'])
      self.dataCenterScalekW = self.convert_to_kw(self.dataCenterScalekW)
      
      self.RacksPerRow = RacksPerRow
      self.rows_per_pod = rows_per_pod
      self.SafeTyMargin = SafeTyMargin
      self.__clearData()

        
    def convert_to_kw(self,power_str):
        if type(power_str) != str :
          return power_str 

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
    




    def findRedundancyPattern(self, stream):
        
      # This regex looks for: N, then +, then digits (r)  E.g. N+1, N+2...
      stream = stream.strip()
      match  = re.fullmatch(r'N\s*\+\s*(\d+)', stream)    
      if match:
          r = int(match.group(1))
          return {'type':self.RedundancySetups.N_plus_r,'r':r}

      #Pattern: xN/y
      match = re.fullmatch(r'(\d+)\s*N\s*/\s*(\d+)', stream)
      if match:
          return {'type':self.RedundancySetups.x_N_over_y,'x':int(match.group(1)), 'y': int(match.group(2))}

      #  Pattern: xN (assume y = 1)
      match = re.fullmatch(r'(\d+)\s*N', stream)
      if match:
        return {'type':self.RedundancySetups.x_N_over_y,'x':int(match.group(1)), 'y': 1}

      # Pattern: N/y (assume x = 1)
      match = re.fullmatch(r'N\s*/\s*(\d+)', stream)
      if match:
          return {'type':self.RedundancySetups.x_N_over_y,'x':1, 'y': int(match.group(1))}

      # 4. Pattern: just N (assume x = 1, y = 1)
      match = re.fullmatch(r'N', stream)
      if match:
        return {'type':self.RedundancySetups.x_N_over_y,'x':1, 'y': 1}

      return None  # If pattern is not found
    
    

    def arrange_racks_per_pod(self):
      """
      Arrange racks using a greedy Largest-Processing-Time (LPT) heuristic.
      n_list: list of counts [n1, n2, n3]
      p_list: list of powers [p1, p2, p3]
      rack_per_pod: max racks per pod
      """

      # Build item list
      items = []
      rack_per_pod = self.rows_per_pod * self.RacksPerRow 
      n_list = [ int(x) for _,x in self.it_config['Rack count'].items() ]
      p_list = [1e3*x for _,x in self.it_config['Peak power (MW)'].items() ]

      for n, p in zip(n_list, p_list):
          if n >0:
            items += [round(float(p/n),1)] * n     #p is total power. dividing by n gives the power per rack

      items.sort(reverse=True)

      N = len(items)
      R = (N + rack_per_pod - 1) // rack_per_pod  # minimal pods // is integer division. THis operation is equivalent to math.ceil()

      import heapq
      heap = [(0, 0, r) for r in range(R)]  # (current_power, count, row_id)
      heapq.heapify(heap)

      pods = [[] for _ in range(R)]
      powers = [0]*R
      counts = [0]*R

      for p in items:
          while True:
              cur_power, cur_count, r = heapq.heappop(heap)
              if counts[r] < rack_per_pod:
                  break

          pods[r].append(p)
          counts[r] += 1
          powers[r] += p

          heapq.heappush(heap, (powers[r], counts[r], r))

      return len(pods), max(powers)


    def ComputeHardwareConfig(self, equipmentType, specificHardwareList='All', redundancy =''):
          try:
        
            System = {}
            ConfigFile = ''
            for outer_key, innerDict in self.HardwareDesigns.items():
              if equipmentType in innerDict.keys():
                System = innerDict[equipmentType]
                ConfigFile =   self.hardwareConfigFilesDir + System["ConfigFile"]
                break
            with open(ConfigFile , 'r') as file:
              data =json.load(file)
            if specificHardwareList == "All":
              if not data:
                print(f"No data found in {ConfigFile}")
                return {}
              specificHardwareList = list(data.keys())
            else:
              for item in specificHardwareList:
                if item not in data:
                  print(f"{item} not found in {ConfigFile }")
                  return {}

            if redundancy  :
                if type(redundancy) == str :
                  Redundancy = self.findRedundancyPattern(redundancy)

            Result = {}

            if self.DesignStep == self.ITvsFacilityDesignPhase.IT.value :  # IT hardware design phase
              for hardware in specificHardwareList :

                Result[hardware] = {}
                if not redundancy:
                  Redundancy = System["Redundancy"][self.DesignStep]
                  Redundancy = self.findRedundancyPattern(Redundancy)

                  if  System["Design level"] == self.DesignLevel.RowLevel.value :
                    if Redundancy['type'] == self.RedundancySetups.N_plus_r  and Redundancy['r'] >= 0: #N+r type
                      nbr_pods, it_power_per_pod = self.arrange_racks_per_pod()
                      HardwarePerPodCount =  math.ceil((1+ self.SafeTyMargin ) * it_power_per_pod/data[hardware]['Capacity']) + Redundancy['r']
                      CapacityDelivreable = data[hardware]['Capacity'] 
                      TotalHardwareCount =  HardwarePerPodCount * nbr_pods
                      
                    elif  Redundancy['type'] == self.RedundancySetups.x_N_over_y and  Redundancy['x'] >= Redundancy['y'] : #xN/y type
                      
                      CapacityDelivreable = Redundancy['y'] * data[hardware]['Capacity'] / Redundancy['x']
                      nbr_pods, it_power_per_pod = self.arrange_racks_per_pod()
                      HardwarePerPodCount =  math.ceil( (1+ self.SafeTyMargin ) * it_power_per_pod /CapacityDelivreable)
                      HardwarePerPodCount = Redundancy['x'] * math.ceil(HardwarePerPodCount/Redundancy['x'])
                      TotalHardwareCount = nbr_pods * HardwarePerPodCount


                    else :
                      raise ValueError(f"The redundancy provided is unknown. Please provide N+r ((with r >= y ))or xN/y (with x > y ) redundancy. Value found {redundancy}")
                      
                    
                    Result[hardware]['Units per Pod'] = HardwarePerPodCount
                    
                    
                  else : # Datacenter level hardware
                    if Redundancy['type'] == self.RedundancySetups.N_plus_r : #N+r type
                      CapacityDelivreable = data[hardware]['Capacity']
                      TotalHardwareCount =   math.ceil( (1+ self.SafeTyMargin ) * self.dataCenterScalekW /data[hardware]['Capacity'] ) + Redundancy['r']

                    elif  Redundancy['type'] == self.RedundancySetups.x_N_over_y : #xN/y type
                      CapacityDelivreable = Redundancy['y'] * data[hardware]['Capacity'] / Redundancy['x']
                      TotalHardwareCount =   math.ceil( (1+ self.SafeTyMargin ) * self.dataCenterScalekW /CapacityDelivreable )
                      TotalHardwareCount = Redundancy['x'] * math.ceil(TotalHardwareCount/Redundancy['x'])

                    else :
                      raise ValueError(f"The redundancy provided is unknown. Please provide N+r ((with r >= y ))or xN/y (with x > y ) redundancy. Value found {redundancy}")


                  spaceUtilization = TotalHardwareCount * data[hardware]['Dimensions']['Depth'] * data[hardware]['Dimensions']['Width']
                  spaceUtilization = round(spaceUtilization * (1 + data[hardware]['AccessAreaShare']),1)

                  Result[hardware]['Total hardware count'] = TotalHardwareCount
                  Result[hardware]['Total Capacity (MW)'] = round(TotalHardwareCount * data[hardware]['Capacity']/1e3,3) #MW
                  Result[hardware]['Space Utilization (m²)'] = spaceUtilization
                  Result[hardware]['Space Efficiency (kW/m²)'] =  round(self.dataCenterScalekW/spaceUtilization,2)

                  if "PeakPowerConsumption" in data[hardware].keys() :
                    Result[hardware]["Maximum power demand (MW)"] = TotalHardwareCount * data[hardware]['PeakPowerConsumption']

                    if  Redundancy['type'] == self.RedundancySetups.x_N_over_y : #xN/y type
                        Result[hardware]["Maximum power demand (MW)"] = Redundancy['y'] * Result[hardware]["Maximum power demand (MW)"]/Redundancy['x']

                    Result[hardware]["Power Efficiency"] =  round(self.dataCenterScalekW / Result[hardware]["Maximum power demand (MW)"],2)
                    Result[hardware]["Maximum power demand (MW)"] = round(Result[hardware]["Maximum power demand (MW)"]/1e3,3) #MW

                  else :
                    Result[hardware]["Power Efficiency"] = data[hardware]['Efficiency']
                    Result[hardware]["Maximum Conversion Power (MW)"] = round( (1-Result[hardware]["Power Efficiency"]) * TotalHardwareCount * CapacityDelivreable / ( 1e3 * Result[hardware]["Power Efficiency"])  ,3) #MW
           
            else :  # Facility design phase...
              if not self.ITvsFacilityDesignPhase.Facility.value in System["Redundancy"].keys() :
                  return {} 
              
              for hardware in specificHardwareList :
                Result[hardware] = {}
                if not redundancy:
                  Redundancy = System["Redundancy"][self.DesignStep]
                  Redundancy = self.findRedundancyPattern(Redundancy)

                System_ = {}
                for outer_key, System_ in self.EfficientDesigns.items() :
                  if equipmentType in System_.keys():
                    break
                  
                for coolingDesign in self.EfficientDesigns[self.Systems.CoolingSystem.value]["Summary"].keys():
                  if Redundancy['type'] == self.RedundancySetups.N_plus_r  and Redundancy['r'] >= 0 : #N+r type
                        CapacityDelivreable =  data[hardware]['Capacity']
                        TotalHardwareCount =   math.ceil(1e3* (1+ self.SafeTyMargin ) * self.EfficientDesigns[self.Systems.CoolingSystem.value]["Summary"][coolingDesign]["Maximum power demand (MW)"] /CapacityDelivreable )
                  #convet back to kw  when calculating Total Harware count

                  elif  Redundancy['type'] == self.RedundancySetups.x_N_over_y and  Redundancy['x'] >= Redundancy['y']: #xN/y type
                        CapacityDelivreable = Redundancy['y'] * data[hardware]['Capacity'] / Redundancy['x']
                        TotalHardwareCount =   math.ceil(1e3* (1+ self.SafeTyMargin ) * self.EfficientDesigns[self.Systems.CoolingSystem.value]["Summary"][coolingDesign]["Maximum power demand (MW)"] /CapacityDelivreable )
                        #convet back to kw  when calculating Total Harware count
                        TotalHardwareCount = Redundancy['x'] * math.ceil(TotalHardwareCount/Redundancy['x'])

                  else :
                      print(f"The redundancy provided is unknown. Please provide N+r or xN/y redundancy pattern")
                      return {}
                  
                  

                  spaceUtilization = TotalHardwareCount * data[hardware]['Dimensions']['Depth'] * data[hardware]['Dimensions']['Width']
                  spaceUtilization = round(spaceUtilization * (1 + data[hardware]['AccessAreaShare']),1)
                  Result[hardware]['Total hardware count'] = TotalHardwareCount
                  Result[hardware]['Total Capacity (MW)'] = round(TotalHardwareCount * data[hardware]['Capacity']/1e3,1) #MW
                  Result[hardware]['Space Utilization (m²)'] = spaceUtilization
                  Result[hardware]['Space Efficiency (kW/m²)'] = round(1e3*self.EfficientDesigns[self.Systems.CoolingSystem.value]["Summary"][coolingDesign]["Maximum power demand (MW)"]/spaceUtilization,2) 
                  
                  if "PeakPowerConsumption" in data[hardware].keys() :
                      Result[hardware]["Maximum power demand (MW)"] = TotalHardwareCount * data[hardware]['PeakPowerConsumption'] 
                      if  Redundancy['type'] == self.RedundancySetups.x_N_over_y : #xN/y type
                        Result[hardware]["Maximum power demand (MW)"] = Redundancy['y'] * Result[hardware]["Maximum power demand (MW)"]/Redundancy['x']

                      Result[hardware]["Power Efficiency"] =  round(self.EfficientDesigns[1e3*self.Systems.CoolingSystem.value]["Summary"][coolingDesign]["Maximum power demand (MW)"] / Result[hardware]["Maximum power demand (MW)"],2)
                      Result[hardware]["Maximum power demand (MW)"] = round(Result[hardware]["Maximum power demand (MW)"] /1e3,3) #MW

                  else :
                      Result[hardware]["Power Efficiency"] = data[hardware]['Efficiency']
                      Result[hardware]["Maximum Conversion Power (MW)"] = round( (1-Result[hardware]["Power Efficiency"]) * TotalHardwareCount * CapacityDelivreable / ( 1e3 * Result[hardware]["Power Efficiency"])  ,3) #MW

            return Result
          except FileNotFoundError:
            print(f"The file at {ConfigFile} was not found.")
          except json.JSONDecodeError:
            print(f"The file at {ConfigFile } is not valid JSON.")
          except Exception as e:
            print(f"An error occurred 1: {e}")




    def __ComputeDesigns(self,DesignStep,EfficiencyArbitrage,equipmentType, specificHardwareList='All'):
        self.DesignStep = DesignStep
        if not equipmentType in self.NonITHardwareConfig.keys():
          self.NonITHardwareConfig[equipmentType] =  {}
        
        result =  self.ComputeHardwareConfig(equipmentType, specificHardwareList)
        
        if result :
          if not equipmentType in self.NonITHardwareConfig.keys():
            self.NonITHardwareConfig[equipmentType] = {}
          if not EfficiencyArbitrage in self.NonITHardwareConfig[equipmentType].keys():
            self.NonITHardwareConfig[equipmentType][EfficiencyArbitrage] = {}          
          self.NonITHardwareConfig[equipmentType][EfficiencyArbitrage][self.DesignStep] = result 


    def __ComputeEfficientDesigns(self, EfficiencyArbitrage, DesignStep, specificHardwareList='All'):
          self.DesignStep = DesignStep
          # Make sure all the designs are first computed
          for equipmentType_ in self.equipmentTypes :
              
              if self.using_dry_cooling and equipmentType_ == self.equipmentTypes.CoolingTowers: 
                 continue
              if (not self.using_dry_cooling) and equipmentType_ == self.equipmentTypes.DryCoolers: 
                 continue

              equipmentType = equipmentType_.value
              
              Hardware_list_for_this_equipment = 'All'   
              if isinstance(specificHardwareList, dict) and equipmentType in specificHardwareList.keys() and EfficiencyArbitrage in specificHardwareList[equipmentType].keys()  and  self.DesignStep in specificHardwareList[equipmentType][EfficiencyArbitrage].keys():
                Hardware_list_for_this_equipment  = [specificHardwareList[equipmentType][EfficiencyArbitrage][self.DesignStep]]
                
              

              if(not equipmentType in self.NonITHardwareConfig.keys() 
                 or  not EfficiencyArbitrage in self.NonITHardwareConfig[equipmentType].keys()
                 or  not self.DesignStep in self.NonITHardwareConfig[equipmentType].keys()) :
                  self.__ComputeDesigns(self.DesignStep,EfficiencyArbitrage,equipmentType, Hardware_list_for_this_equipment)
              
              if EfficiencyArbitrage in self.NonITHardwareConfig[equipmentType].keys() :
                if self.DesignStep in self.NonITHardwareConfig[equipmentType][EfficiencyArbitrage].keys():
                  if EfficiencyArbitrage == self.EfficiencyArbitrage.SpaceEfficientDesign.value:
                    suffix1 = ' Efficiency (kW/m²)'
                    suffix2 = ' Efficiency'
                  else : 
                    suffix2 = ' Efficiency (kW/m²)'
                    suffix1 = ' Efficiency'
                     
                  #criteria = [EfficiencyArbitrage.split(' ')[0] + ' Efficiency'] + [k.value for k in self.EfficiencyArbitrage if k.value != EfficiencyArbitrage ]   
                  criteria = [EfficiencyArbitrage.split(' ')[0] + suffix1] + [k.value.split(' ')[0] + suffix2 for k in self.EfficiencyArbitrage if k.value != EfficiencyArbitrage ]   

                  mostEfficientConfigName, mostEfficiencyConfig = max(self.NonITHardwareConfig[equipmentType][EfficiencyArbitrage][self.DesignStep].items(), key=lambda item: tuple(item[1][metric] for metric in criteria))

 
                  if not mostEfficiencyConfig:
                    continue 

                  for outer_key, System in self.EfficientDesigns.items():
                      if equipmentType in System.keys() :
                        if  not EfficiencyArbitrage in System[equipmentType].keys() :
                          System[equipmentType][EfficiencyArbitrage] = {}
                      
                        System[equipmentType][EfficiencyArbitrage][self.DesignStep] =  {"Name": mostEfficientConfigName} | mostEfficiencyConfig 
                        
                        break
                


          
    def __ComputeTotalPowerAndSpace(self, System, EfficencyCriterium) :

      for systemType, SystemData in self.EfficientDesigns[System].items():
          if systemType == "Summary":
             continue
          
          


          if System == self.Systems.CoolingSystem.value : 
            PowerKey = 'Maximum power demand (MW)'
          else : 
            PowerKey = 'Maximum Conversion Power (MW)'

          if EfficencyCriterium in SystemData.keys() : 
              if not EfficencyCriterium in self.EfficientDesigns[System]["Summary"].keys() : 
                self.EfficientDesigns[System]["Summary"][EfficencyCriterium] = {}
                self.EfficientDesigns[System]["Summary"][EfficencyCriterium][PowerKey] = 0
                self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"] = { 'In datacenter Floor': 0, "Outside" : 0 }
            
              TotalPower= 0
              TotalSpace_indoor = 0
              TotalSpace_outdoor = 0
              for _t, innerDict in SystemData[EfficencyCriterium].items() :
                  if PowerKey in innerDict.keys() : 
                      TotalPower += innerDict[PowerKey]
                  if systemType in self.HardwareLocation.Indoors.value: 

                    TotalSpace_indoor += innerDict["Space Utilization (m²)"]
                  if systemType in self.HardwareLocation.Outdoors.value: 
                    TotalSpace_outdoor += innerDict["Space Utilization (m²)"]

              self.EfficientDesigns[System]["Summary"][EfficencyCriterium][PowerKey] += TotalPower
              self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['In datacenter Floor'] += TotalSpace_indoor
              self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['Outside'] += TotalSpace_outdoor

              self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['In datacenter Floor'] =  round(self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['In datacenter Floor'] ,1)
              self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['Outside'] =  round(self.EfficientDesigns[System]["Summary"][EfficencyCriterium]["Space Utilization (m²)"]['Outside'] ,1)

              self.EfficientDesigns[System]["Summary"][EfficencyCriterium][PowerKey] = round(self.EfficientDesigns[System]["Summary"][EfficencyCriterium][PowerKey],3)
              

    def __ComputeSpaceUtilizationByHardwareTypes_(self, EfficencyCriterium):
      Result = {}
      for _,System in  self.EfficientDesigns.items() :
        for item, SystemData in System.items():
            if item == "Summary":
              continue

            if isinstance(item, Enum) :
              item = item.value 
            if EfficencyCriterium in SystemData.keys() : 
                if not EfficencyCriterium in Result.keys() : 
                  Result[EfficencyCriterium] = {}
                if not item in Result[EfficencyCriterium].keys() :
                  Result[EfficencyCriterium][item] = 0
                
                for t, innerDict in SystemData[EfficencyCriterium].items() :
                    Result[EfficencyCriterium][item] += innerDict["Space Utilization (m²)"]
      return Result

    def getSpaceUtilizationByHardwareTypes(self) -> dict:
      Result = {}
      for EfficencyCriterium in self.EfficiencyArbitrage:
        r = self.__ComputeSpaceUtilizationByHardwareTypes_(EfficencyCriterium.value)
        Result |= r
        
      return Result
    
    

    def __ComputePowerByHardwareTypes_(self, System, EfficencyCriteria  = "All"):
      Result = {}
      #print(self.EfficientDesigns)
    
      if not System in  self.EfficientDesigns.keys() :
        return {}
      
      if EfficencyCriteria == "All": 
          EfficencyCriteria = self.EfficiencyArbitrage

      for EfficencyCriterium_ in EfficencyCriteria :
        EfficencyCriterium = EfficencyCriterium_.value
        for item, SystemData in self.EfficientDesigns[System].items():
            if item == "Summary":
              continue
            
            if isinstance(item, Enum) :
              item = item.value 
            if EfficencyCriterium in SystemData.keys() : 
                for t_, innerDict in SystemData[EfficencyCriterium].items() :
                    if "Maximum power demand (MW)" in innerDict.keys() and System == self.Systems.CoolingSystem.value:
                      if not EfficencyCriterium in Result.keys() : 
                        Result[EfficencyCriterium] = {}
                      Result[EfficencyCriterium][item] = innerDict["Maximum power demand (MW)"]

                    if "Power Efficiency" in innerDict.keys() and System == self.Systems.PowerSystem.value :
                      if not EfficencyCriterium in Result.keys() : 
                        Result[EfficencyCriterium] = {}
                      Result[EfficencyCriterium][item +'-' + t_] = innerDict["Power Efficiency"]
      return Result
    
    def saveEfficientConfigsToCSV(self, file_path='')  : 
      def flatten_entry(path, entry):
          items = ['Equipment type', 'Design metric', "Subsystem"]
          """Flatten a dictionary with a given path, adding path as keys."""
          flat = {}
          for item, key in zip(items,path):
              flat[item] = key
          for k, v in entry.items():
              flat[k] = v
          return flat

      def recursive_flatten(data, path=None):
          """Recursively traverse nested dictionaries to flatten all leaf entries."""
          path = path or []
          rows = []

          if isinstance(data, dict):
              for k, v in data.items():
                  if isinstance(v, dict):
                      if all(not isinstance(i, dict) for i in v.values()):
                          # Leaf-level dictionary (actual data values)
                          rows.append(flatten_entry(path + [k], v))
                      else:
                          rows.extend(recursive_flatten(v, path + [k]))
          return rows

      # Process each top-level system and store per sheet
      keymap = {'Total Capacity': 'Total Capacity(MW)', 'Space Utilization (m²)': f'Space Utilization (m²)', 'Space Efficiency (kW/m²)' : f'Space Efficiency (kW/m²)', 'Maximum power demand (MW)':f'Maximum power demand (MW)' }
      dfs_by_sheet = {}
      for top_level_key, system_data in self.EfficientDesigns.items():
          rows = recursive_flatten(system_data)
          df = pd.DataFrame(rows)
          df = df.rename(columns= keymap)
          dfs_by_sheet[top_level_key] = df

      # Save to Excel
      if file_path =='' : 
        file_path = "DatacenterConfigs.xlsx"
      if not file_path.endswith('.xlsx'):
        file_path = os.path.splitext(file_path)[0] + '.xlsx'
      if os.path.exists(file_path):   
          with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            for sheet_name, df in dfs_by_sheet.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Excel sheet names max out at 31 chars
      else:
          with pd.ExcelWriter(file_path, engine="openpyxl", mode="w") as writer:
            for sheet_name, df in dfs_by_sheet.items():
                df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    def getCoolingHardwarePowerConsumption(self) -> dict:
     return self.__ComputePowerByHardwareTypes_(self.Systems.CoolingSystem.value)
       


    def getPowerDistributionHardwareEfficiency(self) -> dict:
     return self.__ComputePowerByHardwareTypes_(self.Systems.PowerSystem.value)
       
      

    def ComputeSpaceEfficientDesignsForIT(self, specificHardwareList='All'):
        self.__ComputeEfficientDesigns( self.EfficiencyArbitrage.SpaceEfficientDesign.value,self.ITvsFacilityDesignPhase.IT.value, specificHardwareList )
        self.__ComputeTotalPowerAndSpace(self.Systems.CoolingSystem.value, self.EfficiencyArbitrage.SpaceEfficientDesign.value)


    def ComputePowerEfficientDesignsForIT(self, specificHardwareList='All'):
        self.__ComputeEfficientDesigns( self.EfficiencyArbitrage.PowerEfficientDesign.value, self.ITvsFacilityDesignPhase.IT.value, specificHardwareList)
        self.__ComputeTotalPowerAndSpace(self.Systems.CoolingSystem.value, self.EfficiencyArbitrage.PowerEfficientDesign.value)

    def ComputeSpaceEfficientDesignsForFacility(self, specificHardwareList='All'):
        self.__ComputeEfficientDesigns( self.EfficiencyArbitrage.SpaceEfficientDesign.value, self.ITvsFacilityDesignPhase.Facility.value, specificHardwareList )
        self.__ComputeTotalPowerAndSpace(self.Systems.PowerSystem.value, self.EfficiencyArbitrage.SpaceEfficientDesign.value)



    def ComputePowerEfficientDesignsForFacility(self, specificHardwareList='All'):
          self.__ComputeEfficientDesigns( self.EfficiencyArbitrage.PowerEfficientDesign.value, self.ITvsFacilityDesignPhase.Facility.value, specificHardwareList)
          self.__ComputeTotalPowerAndSpace(self.Systems.PowerSystem.value, self.EfficiencyArbitrage.PowerEfficientDesign.value)



    def ComputeDatacenterSpaceEfficientCoolingAndPowerSystems(self, specificHardwareList='All'):
        self.ComputeSpaceEfficientDesignsForIT(specificHardwareList)
        self.ComputeSpaceEfficientDesignsForFacility(specificHardwareList)


    def ComputeDatacenterPowerEfficientCoolingAndPowerSystems(self, specificHardwareList='All'):

        self.ComputePowerEfficientDesignsForIT(specificHardwareList)
        self.ComputePowerEfficientDesignsForFacility(specificHardwareList)

    """def costumize_cooling_system_config (self,specificHardwareList='All' )
       if specificHardwareList=='All' :
          return # nothing to do"""

    def getPowerEfficientConfigurations(self) :
       return {self.Systems.CoolingSystem.value.value : self.EfficientDesigns[self.Systems.CoolingSystem.value]["Summary"], 
               self.Systems.PowerSystem.value.value : self.EfficientDesigns[self.Systems.PowerSystem.value]["Summary"] }

    def getNonITConfigurations(self) : 
       return self.EfficientDesigns 
       
    def getNonITHardwareNames(self, specificEquipmentTypes = "All") :
      result = {}
  
      for system_category in self.EfficientDesigns :
          for subsystem, efficiencies in self.EfficientDesigns[system_category].items():
              if subsystem == 'Summary' or ( specificEquipmentTypes != "All"  and not subsystem in  specificEquipmentTypes)  : 
                continue  # skip aggregation summaries

              if subsystem not in result:
                  result[subsystem] = {}

              for efficiency_type, entity in efficiencies.items():
                  if efficiency_type not in result[subsystem]:
                      result[subsystem][efficiency_type] = {}

                  for role, values in entity.items():
                      if isinstance(values, dict) and 'Name' in values:
                          result[subsystem][efficiency_type][role] = values['Name']
      return result
    
      
            
    def format_specific_non_it_hardware (self, specific_non_IT_hardware = {'Heat Rejection' : 'Name', 
                                            'Chillers': 'Name ',
                                            'CDUs': 'CoolChip100',
                                            'PDUs': 'Name',
                                            'UPS': { 'IT': 'Name', 'Facility': 'Name'}, 
                                            'MSBs':  {'IT': 'Name', 'Facility': 'Name'}, 
                                            'Backup Generators': {'IT': 'Name', 'Facility': 'Name'}
                                            }, Efficiency_modes = {'Space', 'Power'}
                                  ) : 
      specific_hardware = {}
      if 'Heat Rejection' in specific_non_IT_hardware and not  self.using_dry_cooling : 
         specific_hardware['Evaporative Cooling Towers'] = {}
         for efficiency in Efficiency_modes: 
           specific_hardware['Evaporative Cooling Towers'][efficiency] = {'IT' : specific_non_IT_hardware['Heat Rejection']} 

      if 'Heat Rejection' in specific_non_IT_hardware and self.using_dry_cooling : 
         specific_hardware['Dry coolers'] = {}
         for efficiency in Efficiency_modes: 
           specific_hardware['Dry coolers'][efficiency] = {'IT' : specific_non_IT_hardware['Heat Rejection']} 
      
      for key_, value in specific_non_IT_hardware.items(): 
        key = key_
        if key == 'Heat Rejection'  and not  self.using_dry_cooling : 
          key = 'Evaporative Cooling Towers' 
          
        if key == 'Heat Rejection' and self.using_dry_cooling : 
          key= 'Dry coolers'

        specific_hardware[key] = {}
        if key in ['Evaporative Cooling Towers', 'Dry coolers', "Chillers", 'CDUs', "PDUs"] :
          for efficiency in Efficiency_modes: 

            specific_hardware[key][efficiency.capitalize() + 'Optimized Design' ] = {'IT' : value} 

        if key in ['Evaporative Cooling Towers', 'Dry coolers', "Chillers", 'CDUs', "PDUs"] :
                  for efficiency in Efficiency_modes: 
                    specific_hardware[key][efficiency + 'Optimized Design' ] = value

      return specific_hardware


    

    def get_available_hardware(self, Hardware_list = "All") :
      if isinstance(Hardware_list, str) :
        if Hardware_list.capitalize() =="All" or Hardware_list.capitalize() =="Default" : 
          Hardware_list = [ x.value for x in self.equipmentTypes ]
      
      HardwareList = {}

      if 'Heat Rejection' in Hardware_list and not  self.using_dry_cooling : 
          Hardware_list = ["Evaporative Cooling Towers" if item == "Heat Rejection" else item for item in Hardware_list]
          
      if  'Heat Rejection' in Hardware_list and self.using_dry_cooling : 
          Hardware_list = ["Dry coolers" if item == "Heat Rejection" else item for item in Hardware_list]

        
      for outer_key, innerDict in self.HardwareDesigns.items():
          for hw_in_system in innerDict.keys():
            if hw_in_system in Hardware_list:
              System = innerDict[hw_in_system]
              ConfigFile =   self.hardwareConfigFilesDir + System["ConfigFile"]

              try:
                with open(ConfigFile , 'r') as file:
                  data =json.load(file)
                  HardwareList[hw_in_system] = list(data.keys())
              except FileNotFoundError:
                print(f"The file at {ConfigFile} was not found.")
              except json.JSONDecodeError:
                print(f"The file at {ConfigFile } is not valid JSON.")
              except Exception as e:
                print(f"An error occurred 2: {e}")
      return HardwareList
          