clear
insheet using "Roster_2_3.tab", tab case names

label variable Roster_2_3__id `"Id in Roster_2_3"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label variable row `"VARIABLE: row - Stores the rowcode for this HH member"'

label variable Q2_3_1a `"VARIABLE: Q2_3_1 - HH members name"'

label define Q2_3_2 1 `"Male"' 2 `"Female"' 
label values Q2_3_2 Q2_3_2
label variable Q2_3_2 `"Q2_3_2"'

label variable Q2_3_3a `"Q2_3_3a"'

label variable Q2_3_3b `"VARIABLE: Q2_3_3b - HH members age"'

label define Q2_3_4 1 `"Yes"' 0 `"No"' 
label values Q2_3_4 Q2_3_4
label variable Q2_3_4 `"Q2_3_4"'

label define Q2_3_5 1 `"Yes"' 0 `"No"' 
label values Q2_3_5 Q2_3_5
label variable Q2_3_5 `"Q2_3_5"'

label variable Q2_3_6 `"Q2_3_6"'

label variable Q2_3_7 `"Q2_3_7"'

label variable Q2_3_8 `"Q2_3_8"'

label variable Q2_3_1 `"Roster list question"'

label variable interview__id `"Unique 32-character long identifier of the interview"'
