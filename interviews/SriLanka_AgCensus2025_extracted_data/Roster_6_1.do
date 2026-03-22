clear
insheet using "Roster_6_1.tab", tab case names

label define Roster_6_1__id 0 `"No permanent or semi-permanent crops grown on this parcel"' 11 `"Tea"' 12 `"Rubber"' 13 `"Coconuts"' 14 `"Avocados"' 15 `"Bananas"' 16 `"Mangoes"' 17 `"Guava"' 18 `"Mangosteen"' 19 `"Papayas"' 20 `"Pineapples"' 21 `"Rambutan"' 22 `"Durian"' 23 `"Passion Fruit"' 24 `"Dragon Fruit"' 25 `"Pomegranate"' 26 `"Jak"' 27 `"Bread Fruit"' 28 `"Lemons and limes"' 29 `"Oranges"' 30 `"Grapes"' 31 `"Strawberries"' 32 `"Pears and quinces"' 33 `"Cashew nuts"' 34 `"Kathurumurunga"' 35 `"Drumstick"' 36 `"Areca nuts"' 37 `"Palmyrah"' 38 `"Kitul"' 39 `"King Coconut"' 40 `"Oil Palm"' 41 `"Coffee"' 42 `"Cocoa"' 43 `"Pepper (piper spp.)"' 44 `"Nutmeg, mace"' 45 `"Cardamoms"' 46 `"Cinnamon (canella)"' 47 `"Cloves"' 48 `"Goraka"' 49 `"Sugar cane"' 50 `"Betel"' 51 `"Teak"' 52 `"Bhuta"' 53 `"Nedun"' 54 `"Mahogany"' 55 `"Turpentine (Eucalyptus)"' 56 `"Finesse"' 57 `"Agawood"' 58 `"White Incense"' 59 `"Grass Farming"' 60 `"Plant Nursery (permanent/Semi-permanent/mixed)"' 99 `"Other permanent or Semi-permanent crops"' 
label values Roster_6_1__id Roster_6_1__id
label variable Roster_6_1__id `"Id in Roster_6_1"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label define Q6_2 1 `"Systermatic planting only"' 2 `"Scattered planting only"' 
label values Q6_2 Q6_2
label variable Q6_2 `"Q6_2_Method of cultivation"'

label variable Q6_3a `"Q6_3a"'

label variable Q6_3b `"Q6_3b"'

label variable Q6_3c `"Q6_3c"'

label variable Q6_3_dec `"VARIABLE: Q6_3_dec - Convert Q6_3a to decimal acres"'

label variable Q6_3 `"VARIABLE: Q6_3 - Systematic planted area standardized to decimal acres"'

label variable Q6_4a `"Q6_4a"'

label variable Q6_4b `"Q6_4b"'

label variable Q6_4c `"Q6_4c"'

label variable Q6_4_dec `"VARIABLE: Q6_4_dec - Convert Q6_4a to decimal acres"'

label variable Q6_4 `"VARIABLE: Q6_4 - Systematic planted area standardized to decimal acres"'

label variable Q6_5 `"Q6_5"'

label variable Q6_6 `"Q6_6"'

label variable interview__id `"Unique 32-character long identifier of the interview"'

label variable Roster_Q3_3__id `"Id in "Roster_Q3_3""'
