clear
insheet using "Roster_4_1.tab", tab case names

label define Roster_4_1__id 0 `"No paddy or any other seasonal crops grown on this parcel"' 11 `"Rice/Paddy"' 12 `"Maize"' 13 `"Sorghum"' 14 `"Millet"' 15 `"Finger Millet (Kurakkan)"' 16 `"Cabbages"' 17 `"Cauliflower"' 18 `"Lettuce"' 19 `"Spinach"' 20 `"Gotukola"' 21 `"Mukunuwenna"' 22 `"Kankun"' 23 `"Sarana"' 24 `"Thampala"' 25 `"Cabbage Leaves"' 26 `"Kohila"' 27 `"Cucumbers"' 28 `"Egg Plant"' 29 `"Brinjals"' 30 `"Tomatoes"' 31 `"Red Pumpkin"' 32 `"Batana"' 33 `"Kekiri"' 34 `"Gherkin"' 35 `"Ash Pumpkin"' 36 `"Okra (Ladies Finger)"' 37 `"Snake Gourd"' 38 `"Luffa"' 39 `"Bitter Gourd"' 40 `"Thumba Karavila"' 41 `"Carrots"' 42 `"Turnips"' 43 `"Nokol"' 44 `"Beetroot"' 45 `"Red Onions"' 46 `"Big Onions"' 47 `"Leeks and other alliaceous vegetables"' 48 `"Watermelons"' 49 `"Soya beans"' 50 `"Groundnuts"' 51 `"Mustard"' 52 `"Sesame"' 53 `"Potatoes"' 54 `"Sweet potatoes"' 55 `"Cassava"' 56 `"Taro (Cocoyam)"' 57 `"Innala"' 58 `"Chillies (Green)"' 59 `"Capsicum"' 60 `"Ginger"' 61 `"Turmeric"' 62 `"Beans"' 63 `"Cowpeas"' 64 `"Winged Bean"' 65 `"Long Bean"' 66 `"Green Gram"' 67 `"Black Gram"' 68 `"Mushrooms and truffles"' 69 `"Flowers or ornamental plants (seasonal or permanent)"' 70 `"Tobacco"' 71 `"Mixed Crop Plant Nursery"' 99 `"Other Seasonal crops"' 
label values Roster_4_1__id Roster_4_1__id
label variable Roster_4_1__id `"Id in Roster_4_1"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label variable Seasonal_Crop_rowcode `"Seasonal crop row code"'

label variable Q4_5_2a `"Q4_5_2a"'

label variable Q4_5_2b `"Q4_5_2b"'

label variable Q4_5_2c `"Q4_5_2c"'

label variable Q4_5_2_dec `"VARIABLE: Q4_5_2_dec - Convert Q4_5_2a to decimal acres"'

label variable Q4_5_2 `"VARIABLE: Q4_5_2 - Extent sown in Maha season standardized to decimal acres"'

label variable Q4_5_3a `"Q4_5_3a"'

label variable Q4_5_3b `"Q4_5_3b"'

label variable Q4_5_3c `"Q4_5_3c"'

label variable Q4_5_3_dec `"VARIABLE: Q4_5_3_dec - Convert Q4_5_3a to decimal acres"'

label variable Q4_5_3 `"VARIABLE: Q4_5_3 - Extent sown in Yala season standardized to decimal acres"'

label variable interview__id `"Unique 32-character long identifier of the interview"'

label variable Roster_Q3_3__id `"Id in "Roster_Q3_3""'
