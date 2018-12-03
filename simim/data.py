"""
data download functionality
"""

def get_od(nomis_api):

  # get OD data
  # more up-to-date here (E&W by LAD, Scotland & NI by country)
  # https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/migrationwithintheuk/datasets/internalmigrationbyoriginanddestinationlocalauthoritiessexandsingleyearofagedetailedestimatesdataset

  uk_cmlad_codes="1132462081...1132462085,1132462127,1132462128,1132462356...1132462360,1132462086...1132462089,1132462129,1132462130,1132462145...1132462150,1132462229...1132462240,1132462337...1132462351,1132462090...1132462094,1132462269...1132462275,1132462352...1132462355,1132462368...1132462372,1132462095...1132462098,1132462151...1132462158,1132462241...1132462254,1132462262...1132462268,1132462276...1132462282,1132462099...1132462101,1132462131,1132462293...1132462300,1132462319...1132462323,1132462331...1132462336,1132462361...1132462367,1132462111...1132462114,1132462134,1132462135,1132462140...1132462144,1132462178...1132462189,1132462207...1132462216,1132462255...1132462261,1132462301...1132462307,1132462373...1132462404,1132462115...1132462126,1132462136...1132462139,1132462173...1132462177,1132462196...1132462206,1132462217...1132462228,1132462283...1132462287,1132462308...1132462318,1132462324...1132462330,1132462102,1132462103,1132462132,1132462133,1132462104...1132462110,1132462159...1132462172,1132462190...1132462195,1132462288...1132462292,1132462405...1132462484"
  table = "MM01CUK_ALL"
  query_params = {
    "date": "latest",
    "usual_residence": uk_cmlad_codes,
    "address_one_year_ago": uk_cmlad_codes,
    "age": 0,
    "c_sex": 0,
    "measures": 20100,
    "select": "ADDRESS_ONE_YEAR_AGO_CODE,USUAL_RESIDENCE_CODE,OBS_VALUE"
  }
  od = nomis_api.get_data(table, query_params)
  #print(od_2011.USUAL_RESIDENCE_CODE.unique())
  return od

def get_people(ew_api, sc_api, ni_api):
    # people - use ukpopulation
  query_params = {
    "date": "latest",
    "RURAL_URBAN": "0",
    "CELL": "0",
    "MEASURES": "20100",
    "geography": "1946157057...1946157404",
    "select": "GEOGRAPHY_CODE,OBS_VALUE"
  }
  population = ew_api.get_data("KS102EW", query_params)
  
  pop_sc = sc_api.get_data("KS102SC", "S92000003", "LAD", category_filters={"KS102SC_0_CODE": 0}).drop("KS102SC_0_CODE", axis=1)
  # print(p_2011sc.head())
  # print(len(p_2011sc))
  population = population.append(pop_sc)

  if ni_api:
    #print(census_ni.get_metadata("KS102NI", "LAD"))
    pop_ni = ni_api.get_data("KS102NI", "N92000002", "LAD", category_filters={"KS102NI_0_CODE": 16}).drop("KS102NI_0_CODE", axis=1)
    #print(p_2011ni.head())
    population = population.append(pop_ni)

  population.rename({"OBS_VALUE": "PEOPLE"}, axis=1, inplace=True)
  #print(len(population))
  return population

def get_households(ew_api, sc_api, ni_api):

  # households
  # get total household counts per LAD
  query_params = {
    "date": "latest",
    "RURAL_URBAN": "0",
    "CELL": "0",
    "MEASURES": "20100",
    "geography": "1946157057...1946157404",
    "select": "GEOGRAPHY_CODE,OBS_VALUE"
  }
  households = ew_api.get_data("KS105EW", query_params)
  # get Scotland
  households_sc = sc_api.get_data("KS105SC", "S92000003", "LAD", category_filters={"KS105SC_0_CODE": 0}).drop("KS105SC_0_CODE", axis=1)
  # print(households_sc)
  # print(len(households_sc))
  households = households.append(households_sc)
  #print(len(households))

  if ni_api:
    households_ni = ni_api.get_data("KS105NI", "N92000002", "LAD", category_filters={"KS105NI_0_CODE": 0}).drop("KS105NI_0_CODE", axis=1)
    # print(households_ni)
    # print(len(households_ni))
    households = households.append(households_ni)
    
  households.rename({"OBS_VALUE": "HOUSEHOLDS"}, axis=1, inplace=True)
  return households
