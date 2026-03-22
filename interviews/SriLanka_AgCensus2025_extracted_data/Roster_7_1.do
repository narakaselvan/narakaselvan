clear
insheet using "Roster_7_1.tab", tab case names

label define Roster_7_1__id 11 `"Cattle"' 12 `"Buffaloes"' 13 `"Sheep"' 14 `"Goats"' 15 `"Swine/ pigs"' 16 `"Chickens"' 17 `"Turkeys"' 18 `"Geese"' 19 `"Ducks"' 20 `"Guinea fowls"' 21 `"Quail"' 22 `"Rabbits and hares"' 23 `"Horses"' 24 `"Asses"' 25 `"Bees"' 26 `"Silkworms"' 99 `"Other animals"' 
label values Roster_7_1__id Roster_7_1__id
label variable Roster_7_1__id `"Id in Roster_7_1"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label variable Q7_1_3 `"Q7_1_3"'

label variable Label_Q7_1_3 `"VARIABLE: Label_Q7_1_3 - Stores the right text to display in Q7_1_3"'

label variable Q7_1_4 `"Q7_1_4"'

label variable interview__id `"Unique 32-character long identifier of the interview"'
