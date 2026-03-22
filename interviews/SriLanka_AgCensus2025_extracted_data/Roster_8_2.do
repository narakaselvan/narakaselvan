clear
insheet using "Roster_8_2.tab", tab case names

label define Roster_8_2__id 1 `"Fish"' 2 `"Prawns"' 3 `"Ornamental fish"' 4 `"Sea/ Water plants"' 5 `"Crab/ Sea urchin/ Shell fish"' 0 `"No aquaculture on this parcel"' 
label values Roster_8_2__id Roster_8_2__id
label variable Roster_8_2__id `"Id in Roster_8_2"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label define Q8_2 1 `"Inland water"' 2 `"Brackish water"' 3 `"Marine water"' 
label values Q8_2 Q8_2
label variable Q8_2 `"Q8_2"'

label variable Q8_3__1 `"Q8_3:Tanks"'

label variable Q8_3__2 `"Q8_3:Ponds"'

label variable Q8_3__3 `"Q8_3:Cages"'

label variable Q8_3__4 `"Q8_3:Other"'

label variable Q8_4__1 `"Q8_4:Breeding"'

label variable Q8_4__2 `"Q8_4:Multiplication"'

label variable Q8_4__3 `"Q8_4:Cultivation"'

label variable interview__id `"Unique 32-character long identifier of the interview"'

label variable Roster_Q3_3__id `"Id in "Roster_Q3_3""'
