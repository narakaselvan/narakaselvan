clear
insheet using "Q9_2.tab", tab case names

label define Q9_2__id 11 `"4 wheel tractor"' 12 `"2 wheel tractor"' 13 `"Planting machine"' 14 `"Tiller machines"' 15 `"Seeder"' 16 `"Knapsack sprayer"' 17 `"Motorized sprayer"' 18 `"Combined harvester"' 19 `"Mechanized harvester"' 20 `"Mechanized thresher with blower"' 21 `"Mechanized thresher"' 22 `"Winnowing machine"' 23 `"Drying machines (grains/vegetables/fruits)"' 24 `"Water pump (agriculture)"' 25 `"Milking machine"' 26 `"Milk coolers"' 27 `"Meat cutting machines"' 28 `"Grass cutter (For agricultural purpose)"' 29 `"Tea leaf harvester"' 30 `"Backhoe machines"' 31 `"Other agricultural machines"' 32 `"Instruments that use in aquaculture"' 
label values Q9_2__id Q9_2__id
label variable Q9_2__id `"Id in Q9_2"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label variable Q9_5__1 `"Q9_5:Own"'

label variable Q9_5__2 `"Q9_5:Rented"'

label variable Q9_5__3 `"Q9_5:Other"'

label variable Q9_6 `"Q9_6"'

label variable interview__id `"Unique 32-character long identifier of the interview"'
