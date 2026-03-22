clear
insheet using "SriLanka_AgCensus2025.tab", tab case names

label variable interview__id `"Unique 32-character long identifier of the interview"'

label variable interview__key `"Interview key (identifier in XX-XX-XX-XX format)"'

label variable assignment__id `"Assignment id (identifier in numeric format)"'

label variable sssys_irnd `"Random number in the range 0..1 associated with interview"'

label variable has__errors `"Errors count in the interview"'

label define interview__status 0 `"Restored"' 20 `"Created"' 40 `"SupervisorAssigned"' 60 `"InterviewerAssigned"' 65 `"RejectedBySupervisor"' 80 `"ReadyForInterview"' 85 `"SentToCapi"' 95 `"Restarted"' 100 `"Completed"' 120 `"ApprovedBySupervisor"' 125 `"RejectedByHeadquarters"' 130 `"ApprovedByHeadquarters"' -1 `"Deleted"' 
label values interview__status interview__status
label variable interview__status `"Status of the interview"'

label variable B7 `"B7"'

label variable B8 `"B8"'

label variable A15 `"A15"'

label variable A0 `"A0"'

label variable A01 `"A01"'

label variable A1a `"A1a"'

label variable A1b `"A1b"'

label variable A2a `"A2a"'

label variable A2b `"A2b"'

label variable A3a `"A3a"'

label variable A3b `"A3b"'

label variable A10 `"A10"'

label variable A11a `"A11a"'

label variable A11b `"A11b"'

label variable A12a `"A12a"'

label variable A12b `"A12b"'

label define A13 1 `"Housing unit"' 2 `"Collective living quatre"' 3 `"Residential institute"' 4 `"Non housing unit"' 
label values A13 A13
label variable A13 `"A13"'

label variable A14a `"A14a"'

label variable A14b `"A14b. Case ID"'

label variable ELIGIBLE `"Status:"'

label define A21 1 `"Active/inhabited"' 2 `"Demolished"' 
label values A21 A21
label variable A21 `"A21"'

label variable A17 `"A17_attempt1"'

label define A17a 1 `"Yes"' 0 `"No"' 
label values A17a A17a
label variable A17a `"A17a"'

label variable A18 `"A18_attempt2"'

label define A18a 1 `"Yes"' 0 `"No"' 
label values A18a A18a
label variable A18a `"A18a"'

label variable A19 `"A19_attempt3"'

label define A19a 1 `"Yes"' 0 `"No"' 
label values A19a A19a
label variable A19a `"A19a"'

label define C1 1 `"Household"' 2 `"Non-household"' 
label values C1 C1
label variable C1 `"C1"'

label define C2a 1 `"Yes"' 0 `"No"' 
label values C2a C2a
label variable C2a `"C2a"'

label variable C2b `"C2b"'

label define C3a 1 `"Yes"' 0 `"No"' 
label values C3a C3a
label variable C3a `"C3a"'

label variable C3b `"C3b"'

label define Q1_1 1 `"Yes, Suitable respondent available"' 2 `"No, suitable respondent/refused"' 3 `"Unit temporarily closed"' 4 `"Permanently closed/ vacant unit"' 
label values Q1_1 Q1_1
label variable Q1_1 `"Q1_1"'

label variable Q1_2a `"Q1_2a"'

label variable Q1_2b `"Q1_2b"'

label define Q1_3a 1 `"Yes"' 0 `"No"' 
label values Q1_3a Q1_3a
label variable Q1_3a `"Q1_3a"'

label define Q1_3b 1 `"Yes"' 0 `"No"' 
label values Q1_3b Q1_3b
label variable Q1_3b `"Q1_3b"'

label define Q1_3c 1 `"Yes"' 0 `"No"' 
label values Q1_3c Q1_3c
label variable Q1_3c `"Q1_3c"'

label define Q1_3d 1 `"Yes"' 0 `"No"' 
label values Q1_3d Q1_3d
label variable Q1_3d `"Q1_3d"'

label define Q1_3e 1 `"Yes"' 0 `"No"' 
label values Q1_3e Q1_3e
label variable Q1_3e `"Q1_3e"'

label define Q1_4a 1 `"Civil person (household holding)"' 2 `"Group of civil persons (household holding)"' 3 `"Juridical person (Estate, commercial, institutional holding)"' 
label values Q1_4a Q1_4a
label variable Q1_4a `"Q1_4a"'

label define Q1_4b 1 `"Private/commercial holding"' 2 `"Government holding"' 3 `"Semi-government"' 
label values Q1_4b Q1_4b
label variable Q1_4b `"Q1_4b"'

label define Q1_4c 1 `"Only sales"' 2 `"Both sales & self-consumption"' 3 `"Only self-consumption"' 
label values Q1_4c Q1_4c
label variable Q1_4c `"Q1_4c"'

label define Q1_4d 1 `"Yes"' 0 `"No"' 
label values Q1_4d Q1_4d
label variable Q1_4d `"Q1_4d"'

label define Q1_4e 1 `"Yes"' 0 `"No"' 
label values Q1_4e Q1_4e
label variable Q1_4e `"Q1_4e"'

label define Q1_2c 1 `"Self"' 2 `"Manager"' 3 `"Spouse"' 4 `"Child"' 5 `"Parent"' 6 `"Employee"' 7 `"Other"' 
label values Q1_2c Q1_2c
label variable Q1_2c `"Q1_2c"'

label variable Q1_5 `"VARIABLE: Q1.5. Stores value 1 if eligible, 0 if not eligible"'

label variable Q2_1_1 `"Q2_1_1"'

label variable Q2_1_2 `"Q2_1_2"'

label define Q2_1_3 1 `"Male"' 2 `"Female"' 
label values Q2_1_3 Q2_1_3
label variable Q2_1_3 `"Q2_1_3"'

label variable Q2_1_4 `"Q2_1_4"'

label variable Q2_1_5 `"VARIABLE: Q2_1_5 - Holders age"'

label define Q2_1_6 1 `"Never married"' 2 `"Married"' 3 `"Widowed"' 4 `"Divorced"' 5 `"Seperated"' 
label values Q2_1_6 Q2_1_6
label variable Q2_1_6 `"Q2_1_6"'

label define Q2_1_7 1 `"Never attended school"' 2 `"Passed grade 1"' 3 `"Passed grade 2"' 4 `"Passed grade 3"' 5 `"Passed grade 4"' 6 `"Passed grade 5"' 7 `"Passed grade 6"' 8 `"Passed grade 7"' 9 `"Passed grade 8"' 10 `"Passed grade 9"' 11 `"Passed grade 10"' 12 `"G.C.E. (O/L) or equivalent"' 13 `"G.C.E. (A/L) or equivalent"' 14 `"Degree"' 15 `"Post graduate degree/diploma"' 16 `"Ph.D"' 17 `"Studied/Studying at the special school / special education unit"' 
label values Q2_1_7 Q2_1_7
label variable Q2_1_7 `"Q2_1_7"'

label define Q2_1_8 1 `"Yes"' 0 `"No"' 
label values Q2_1_8 Q2_1_8
label variable Q2_1_8 `"Q2_1_8"'

label define Q2_1_9 1 `"Yes"' 0 `"No"' 
label values Q2_1_9 Q2_1_9
label variable Q2_1_9 `"Q2_1_9"'

label define Q2_1_10a 1 `"All income from Agriculture"' 2 `"Some Income from agriculture, along with other sources of income"' 3 `"No income from agriculture"' 
label values Q2_1_10a Q2_1_10a
label variable Q2_1_10a `"Q2_1_10"'

label variable Q2_1_10b `"VARIABLE: Q2_1_10b - Income from agriculture: 0 if no income from agriculture, 1 if all income from agriculture, 2 if some income from agriculture"'

label variable Q2_1_11__1 `"Q2_1_11:Government/semi-government paid employee"'

label variable Q2_1_11__2 `"Q2_1_11:Private sector paid employee"'

label variable Q2_1_11__3 `"Q2_1_11:Employer (with employees under himself)"'

label variable Q2_1_11__4 `"Q2_1_11:Own account worker (without employees under himself)"'

label variable Q2_1_11__5 `"Q2_1_11:Pensioner"'

label variable Q2_1_11__6 `"Q2_1_11:Income from other sources (Remittance/interest on taxes/fixed deposit income, etc.)"'

label variable Q2_2_1a `"Q2_2_1a"'

label variable Q2_2_1b `"Q2_2_1b"'

label variable Q2_2_2a `"Q2_2_2a"'

label variable Q2_2_2b `"Q2_2_2b"'

label variable Q2_2_3a `"Q2_2_3a"'

label variable Q2_2_3b `"Q2_2_3b"'

label variable Q2_2_4a `"VARIABLE: Q2_2_4a - Total number of male HH members aged 15 or holder"'

label variable Q2_2_4b `"VARIABLE: Q2_2_4b - Total number of female HH members aged 15 or holder"'

label variable Q2_3_1__0 `"Q2_3_1:0"'

label variable Q2_3_1__0c `"Q2_3_1:0c"'

label variable Q2_3_1__1 `"Q2_3_1:1"'

label variable Q2_3_1__1c `"Q2_3_1:1c"'

label variable Q2_3_1__2 `"Q2_3_1:2"'

label variable Q2_3_1__2c `"Q2_3_1:2c"'

label variable Q2_3_1__3 `"Q2_3_1:3"'

label variable Q2_3_1__3c `"Q2_3_1:3c"'

label variable Q2_3_1__4 `"Q2_3_1:4"'

label variable Q2_3_1__4c `"Q2_3_1:4c"'

label variable Q2_3_1__5 `"Q2_3_1:5"'

label variable Q2_3_1__5c `"Q2_3_1:5c"'

label variable Q2_3_1__6 `"Q2_3_1:6"'

label variable Q2_3_1__6c `"Q2_3_1:6c"'

label variable Q2_3_1__7 `"Q2_3_1:7"'

label variable Q2_3_1__7c `"Q2_3_1:7c"'

label variable Q2_3_1__8 `"Q2_3_1:8"'

label variable Q2_3_1__8c `"Q2_3_1:8c"'

label variable Q2_3_1__9 `"Q2_3_1:9"'

label variable Q2_3_1__9c `"Q2_3_1:9c"'

label variable Q2_3_1__10 `"Q2_3_1:10"'

label variable Q2_3_1__10c `"Q2_3_1:10c"'

label variable Q2_3_1__11 `"Q2_3_1:11"'

label variable Q2_3_1__11c `"Q2_3_1:11c"'

label variable Q2_3_1__12 `"Q2_3_1:12"'

label variable Q2_3_1__12c `"Q2_3_1:12c"'

label variable Q2_3_1__13 `"Q2_3_1:13"'

label variable Q2_3_1__13c `"Q2_3_1:13c"'

label variable Q2_3_1__14 `"Q2_3_1:14"'

label variable Q2_3_1__14c `"Q2_3_1:14c"'

label variable Q2_4__1 `"Q2_4:Support activities to agriculture and post-harvest crop activities"'

label variable Q2_4__2 `"Q2_4:Hunting, trapping, and related service activities"'

label variable Q2_4__3 `"Q2_4:Forestry and logging"'

label variable Q2_4__4 `"Q2_4:Manufacturing [Processing of agricultural products (agroprocessing), Handicrafts]"'

label variable Q2_4__5 `"Q2_4:Wholesale and retail trade, repair of motor vehicles and motorcycles"'

label variable Q2_4__6 `"Q2_4:Hotels and restaurants (excluding agrotourism)"'

label variable Q2_4__7 `"Q2_4:Agrotourism"'

label variable Q2_4__8 `"Q2_4:Other"'

label variable Q2_4__9 `"Q2_4:No other economic activities"'

label define Q2_5_1 1 `"Yes"' 0 `"No"' 
label values Q2_5_1 Q2_5_1
label variable Q2_5_1 `"Q2_5_1"'

label variable Q2_5_2a `"Q2_5_2a"'

label define Q2_5_2b 1 `"Male"' 2 `"Female"' 
label values Q2_5_2b Q2_5_2b
label variable Q2_5_2b `"Q2_5_2b"'

label variable Q2_5_2c `"Q2_5_2c"'

label variable Q2_5_2d `"VARIABLE: Q2_5_2d - Managers age"'

label define Q2_5_2e 1 `"Never attended school"' 2 `"Passed grade"' 3 `"Passed grade 2"' 4 `"Passed grade 3"' 5 `"Passed grade 4"' 6 `"Passed grade 5"' 7 `"Passed grade 6"' 8 `"Passed grade 7"' 9 `"Passed grade 8"' 10 `"Passed grade 9"' 11 `"Passed grade 10"' 12 `"G.C.E. (O/L) or equivalent"' 13 `"G.C.E. (A/L) or equivalent"' 14 `"Degree"' 15 `"Post graduate degree/diploma"' 16 `"Ph.D"' 17 `"Studied/Studying at the special school / special education unit"' 
label values Q2_5_2e Q2_5_2e
label variable Q2_5_2e `"Q2_5_2e"'

label define Q2_6_1 1 `"Yes"' 0 `"No"' 
label values Q2_6_1 Q2_6_1
label variable Q2_6_1 `"Q2_6_1"'

label variable Q2_6_2a `"Q2_6_2a"'

label variable Q2_6_2b `"Q2_6_2b"'

label variable Q2_6_2c `"VARIABLE: Q2_6_2c - Total number of employees"'

label variable Q2_6_3a `"Q2_6_3a"'

label variable Q2_6_3b `"Q2_6_3b"'

label variable Q2_6_3c `"VARIABLE: Q2_6_3c - Total number of man-days worked by employees"'

label variable Q2_7a `"VARIABLE: Q2_7a - Name of the selected HH member"'

label variable Q2_7b `"VARIABLE: Q2_7b - Gender of the selected HH member (code)"'

label variable Q2_7c `"VARIABLE: Q2_7c - Age of the selected HH member"'

label define Q2_7d 1 `"Yes"' 0 `"No"' 98 `"Don’t know"' 
label values Q2_7d Q2_7d
label variable Q2_7d `"Q2_7d"'

label define Q2_7e 1 `"Yes"' 0 `"No"' 98 `"Don’t know"' 
label values Q2_7e Q2_7e
label variable Q2_7e `"Q2_7e"'

label define Q2_7f 1 `"Yes"' 0 `"No"' 98 `"Don’t know"' 
label values Q2_7f Q2_7f
label variable Q2_7f `"Q2_7f"'

label variable STR `"VARIABLE: STR - Stores 1 if household member has secure tenure rights to agricultural land, 0 if not."'

label variable Q3_1 `"Q3_1"'

label define Q3_2 1 `"Acres / Roods / Perches"' 2 `"Decimal acres"' 3 `"Hectares"' 
label values Q3_2 Q3_2
label variable Q3_2 `"Q3_2"'

label variable Q3_4__0 `"Q3_4:0"'

label variable Q3_4__0c `"Q3_4:0c"'

label variable Q3_4__1 `"Q3_4:1"'

label variable Q3_4__1c `"Q3_4:1c"'

label variable Q3_4__2 `"Q3_4:2"'

label variable Q3_4__2c `"Q3_4:2c"'

label variable Q3_4__3 `"Q3_4:3"'

label variable Q3_4__3c `"Q3_4:3c"'

label variable Q3_4__4 `"Q3_4:4"'

label variable Q3_4__4c `"Q3_4:4c"'

label variable Q3_4__5 `"Q3_4:5"'

label variable Q3_4__5c `"Q3_4:5c"'

label variable Q3_4__6 `"Q3_4:6"'

label variable Q3_4__6c `"Q3_4:6c"'

label variable Q3_4__7 `"Q3_4:7"'

label variable Q3_4__7c `"Q3_4:7c"'

label variable Q3_4__8 `"Q3_4:8"'

label variable Q3_4__8c `"Q3_4:8c"'

label variable Q3_4__9 `"Q3_4:9"'

label variable Q3_4__9c `"Q3_4:9c"'

label variable Q3_4__10 `"Q3_4:10"'

label variable Q3_4__10c `"Q3_4:10c"'

label variable Q3_4__11 `"Q3_4:11"'

label variable Q3_4__11c `"Q3_4:11c"'

label variable Q3_4__12 `"Q3_4:12"'

label variable Q3_4__12c `"Q3_4:12c"'

label variable Q3_4__13 `"Q3_4:13"'

label variable Q3_4__13c `"Q3_4:13c"'

label variable Q3_4__14 `"Q3_4:14"'

label variable Q3_4__14c `"Q3_4:14c"'

label variable Q3_4__15 `"Q3_4:15"'

label variable Q3_4__15c `"Q3_4:15c"'

label variable Q3_4__16 `"Q3_4:16"'

label variable Q3_4__16c `"Q3_4:16c"'

label variable Q3_4__17 `"Q3_4:17"'

label variable Q3_4__17c `"Q3_4:17c"'

label variable Q3_4__18 `"Q3_4:18"'

label variable Q3_4__18c `"Q3_4:18c"'

label variable Q3_4__19 `"Q3_4:19"'

label variable Q3_4__19c `"Q3_4:19c"'

label variable Q3_4__20 `"Q3_4:20"'

label variable Q3_4__20c `"Q3_4:20c"'

label variable Q3_4__21 `"Q3_4:21"'

label variable Q3_4__21c `"Q3_4:21c"'

label variable Q3_4__22 `"Q3_4:22"'

label variable Q3_4__22c `"Q3_4:22c"'

label variable Q3_4__23 `"Q3_4:23"'

label variable Q3_4__23c `"Q3_4:23c"'

label variable Q3_4__24 `"Q3_4:24"'

label variable Q3_4__24c `"Q3_4:24c"'

label variable Q3_4__25 `"Q3_4:25"'

label variable Q3_4__25c `"Q3_4:25c"'

label variable Q3_4__26 `"Q3_4:26"'

label variable Q3_4__26c `"Q3_4:26c"'

label variable Q3_4__27 `"Q3_4:27"'

label variable Q3_4__27c `"Q3_4:27c"'

label variable Q3_4__28 `"Q3_4:28"'

label variable Q3_4__28c `"Q3_4:28c"'

label variable Q3_4__29 `"Q3_4:29"'

label variable Q3_4__29c `"Q3_4:29c"'

label variable Q3_4__30 `"Q3_4:30"'

label variable Q3_4__30c `"Q3_4:30c"'

label variable Q3_4__31 `"Q3_4:31"'

label variable Q3_4__31c `"Q3_4:31c"'

label variable Q3_4__32 `"Q3_4:32"'

label variable Q3_4__32c `"Q3_4:32c"'

label variable Q3_4__33 `"Q3_4:33"'

label variable Q3_4__33c `"Q3_4:33c"'

label variable Q3_4__34 `"Q3_4:34"'

label variable Q3_4__34c `"Q3_4:34c"'

label variable Q3_4__35 `"Q3_4:35"'

label variable Q3_4__35c `"Q3_4:35c"'

label variable Q3_4__36 `"Q3_4:36"'

label variable Q3_4__36c `"Q3_4:36c"'

label variable Q3_4__37 `"Q3_4:37"'

label variable Q3_4__37c `"Q3_4:37c"'

label variable Q3_4__38 `"Q3_4:38"'

label variable Q3_4__38c `"Q3_4:38c"'

label variable Q3_4__39 `"Q3_4:39"'

label variable Q3_4__39c `"Q3_4:39c"'

label variable Q3_4__40 `"Q3_4:40"'

label variable Q3_4__40c `"Q3_4:40c"'

label variable Q3_4__41 `"Q3_4:41"'

label variable Q3_4__41c `"Q3_4:41c"'

label variable Q3_4__42 `"Q3_4:42"'

label variable Q3_4__42c `"Q3_4:42c"'

label variable Q3_4__43 `"Q3_4:43"'

label variable Q3_4__43c `"Q3_4:43c"'

label variable Q3_4__44 `"Q3_4:44"'

label variable Q3_4__44c `"Q3_4:44c"'

label variable Q3_4__45 `"Q3_4:45"'

label variable Q3_4__45c `"Q3_4:45c"'

label variable Q3_4__46 `"Q3_4:46"'

label variable Q3_4__46c `"Q3_4:46c"'

label variable Q3_4__47 `"Q3_4:47"'

label variable Q3_4__47c `"Q3_4:47c"'

label variable Q3_4__48 `"Q3_4:48"'

label variable Q3_4__48c `"Q3_4:48c"'

label variable Q3_4__49 `"Q3_4:49"'

label variable Q3_4__49c `"Q3_4:49c"'

label variable Q3_4__50 `"Q3_4:50"'

label variable Q3_4__50c `"Q3_4:50c"'

label variable Q3_4__51 `"Q3_4:51"'

label variable Q3_4__51c `"Q3_4:51c"'

label variable Q3_4__52 `"Q3_4:52"'

label variable Q3_4__52c `"Q3_4:52c"'

label variable Q3_4__53 `"Q3_4:53"'

label variable Q3_4__53c `"Q3_4:53c"'

label variable Q3_4__54 `"Q3_4:54"'

label variable Q3_4__54c `"Q3_4:54c"'

label variable Q3_4__55 `"Q3_4:55"'

label variable Q3_4__55c `"Q3_4:55c"'

label variable Q3_4__56 `"Q3_4:56"'

label variable Q3_4__56c `"Q3_4:56c"'

label variable Q3_4__57 `"Q3_4:57"'

label variable Q3_4__57c `"Q3_4:57c"'

label variable Q3_4__58 `"Q3_4:58"'

label variable Q3_4__58c `"Q3_4:58c"'

label variable Q3_4__59 `"Q3_4:59"'

label variable Q3_4__59c `"Q3_4:59c"'

label variable Q3_4__60 `"Q3_4:60"'

label variable Q3_4__60c `"Q3_4:60c"'

label variable Q3_4__61 `"Q3_4:61"'

label variable Q3_4__61c `"Q3_4:61c"'

label variable Q3_4__62 `"Q3_4:62"'

label variable Q3_4__62c `"Q3_4:62c"'

label variable Q3_4__63 `"Q3_4:63"'

label variable Q3_4__63c `"Q3_4:63c"'

label variable Q3_4__64 `"Q3_4:64"'

label variable Q3_4__64c `"Q3_4:64c"'

label variable Q3_4__65 `"Q3_4:65"'

label variable Q3_4__65c `"Q3_4:65c"'

label variable Q3_4__66 `"Q3_4:66"'

label variable Q3_4__66c `"Q3_4:66c"'

label variable Q3_4__67 `"Q3_4:67"'

label variable Q3_4__67c `"Q3_4:67c"'

label variable Q3_4__68 `"Q3_4:68"'

label variable Q3_4__68c `"Q3_4:68c"'

label variable Q3_4__69 `"Q3_4:69"'

label variable Q3_4__69c `"Q3_4:69c"'

label variable Q3_4__70 `"Q3_4:70"'

label variable Q3_4__70c `"Q3_4:70c"'

label variable Q3_4__71 `"Q3_4:71"'

label variable Q3_4__71c `"Q3_4:71c"'

label variable Q3_4__72 `"Q3_4:72"'

label variable Q3_4__72c `"Q3_4:72c"'

label variable Q3_4__73 `"Q3_4:73"'

label variable Q3_4__73c `"Q3_4:73c"'

label variable Q3_4__74 `"Q3_4:74"'

label variable Q3_4__74c `"Q3_4:74c"'

label variable Q3_4__75 `"Q3_4:75"'

label variable Q3_4__75c `"Q3_4:75c"'

label variable Q3_4__76 `"Q3_4:76"'

label variable Q3_4__76c `"Q3_4:76c"'

label variable Q3_4__77 `"Q3_4:77"'

label variable Q3_4__77c `"Q3_4:77c"'

label variable Q3_4__78 `"Q3_4:78"'

label variable Q3_4__78c `"Q3_4:78c"'

label variable Q3_4__79 `"Q3_4:79"'

label variable Q3_4__79c `"Q3_4:79c"'

label variable Q3_4__80 `"Q3_4:80"'

label variable Q3_4__80c `"Q3_4:80c"'

label variable Q3_4__81 `"Q3_4:81"'

label variable Q3_4__81c `"Q3_4:81c"'

label variable Q3_4__82 `"Q3_4:82"'

label variable Q3_4__82c `"Q3_4:82c"'

label variable Q3_4__83 `"Q3_4:83"'

label variable Q3_4__83c `"Q3_4:83c"'

label variable Q3_4__84 `"Q3_4:84"'

label variable Q3_4__84c `"Q3_4:84c"'

label variable Q3_4__85 `"Q3_4:85"'

label variable Q3_4__85c `"Q3_4:85c"'

label variable Q3_4__86 `"Q3_4:86"'

label variable Q3_4__86c `"Q3_4:86c"'

label variable Q3_4__87 `"Q3_4:87"'

label variable Q3_4__87c `"Q3_4:87c"'

label variable Q3_4__88 `"Q3_4:88"'

label variable Q3_4__88c `"Q3_4:88c"'

label variable Q3_4__89 `"Q3_4:89"'

label variable Q3_4__89c `"Q3_4:89c"'

label variable Q3_4__90 `"Q3_4:90"'

label variable Q3_4__90c `"Q3_4:90c"'

label variable Q3_4__91 `"Q3_4:91"'

label variable Q3_4__91c `"Q3_4:91c"'

label variable Q3_4__92 `"Q3_4:92"'

label variable Q3_4__92c `"Q3_4:92c"'

label variable Q3_4__93 `"Q3_4:93"'

label variable Q3_4__93c `"Q3_4:93c"'

label variable Q3_4__94 `"Q3_4:94"'

label variable Q3_4__94c `"Q3_4:94c"'

label variable Q3_4__95 `"Q3_4:95"'

label variable Q3_4__95c `"Q3_4:95c"'

label variable Q3_4__96 `"Q3_4:96"'

label variable Q3_4__96c `"Q3_4:96c"'

label variable Q3_4__97 `"Q3_4:97"'

label variable Q3_4__97c `"Q3_4:97c"'

label variable Q3_4__98 `"Q3_4:98"'

label variable Q3_4__98c `"Q3_4:98c"'

label variable Q3_4__99 `"Q3_4:99"'

label variable Q3_4__99c `"Q3_4:99c"'

label define Q3_10 1 `"Yes"' 0 `"No"' 
label values Q3_10 Q3_10
label variable Q3_10 `"Q3_10"'

label define Q3_11a 1 `"Yes"' 0 `"No"' 
label values Q3_11a Q3_11a
label variable Q3_11a `"Q3_11a"'

label variable Q3_11ba `"Q3_11ba"'

label variable Q3_11bb `"Q3_11bb"'

label variable Q3_11bc `"Q3_11bc"'

label variable Q3_11b_dec `"VARIABLE: Q3_11b_dec - Convert Q3_11ba to decimal acres"'

label variable Q3_11b `"VARIABLE: Q3_11b - Area owned and rented out standardized to decimal acres"'

label variable Q3_12 `"VARIABLE: Q3_12 - Agricultural area owned and operated in decimal acres"'

label variable Q3_13 `"VARIABLE: Q3_13 - Agricultural area rented in and operated in decimal acres"'

label variable Q3_14 `"VARIABLE: Q3_14 - Agricultural area operated in decimal acres"'

label variable Q3_15 `"VARIABLE: Q3_15 - Agricultural area owned in decimal acres"'

label variable Q3_16 `"VARIABLE: Q3_16 - Total holding area in decimal acres"'

label define Q4_0 1 `"Yes"' 0 `"No"' 
label values Q4_0 Q4_0
label variable Q4_0 `"Q4_0"'

label define Q4_1 1 `"Both 2024/25 Maha and 2025 Yala seasons"' 2 `"Only 2024/25 Maha season"' 3 `"Only 2025 Yala season"' 
label values Q4_1 Q4_1
label variable Q4_1 `"Q4_1"'

label define Q4_2a 1 `"Yes"' 0 `"No"' 
label values Q4_2a Q4_2a
label variable Q4_2a `"Q4_2a"'

label variable Q4_2b__1 `"Q4_2b:Within a greenhouse"'

label variable Q4_2b__2 `"Q4_2b:Hydroponic method"'

label variable Q4_2b__3 `"Q4_2b:Drone technology"'

label variable Q4_2b__4 `"Q4_2b:AI technology"'

label variable Q4_2b__5 `"Q4_2b:Other"'

label variable Q4_2c `"Q4_2c"'

label variable Q4_2d `"Q4_2d"'

label define Q4_3a 1 `"Yes"' 0 `"No"' 
label values Q4_3a Q4_3a
label variable Q4_3a `"Q4_3a"'

label variable Q4_3b__1 `"Q4_3b:Major"'

label variable Q4_3b__2 `"Q4_3b:Minor"'

label variable Q4_3b__3 `"Q4_3b:Rainfed"'

label variable Q4_3b__4 `"Q4_3b:Agriculture wells/ponds"'

label variable Q4_3b__5 `"Q4_3b:Tube wells (ground water)"'

label variable Q4_3b__6 `"Q4_3b:Other (specify)"'

label variable Q4_3c `"Q4_3c"'

label define Q4_4a 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q4_4a Q4_4a
label variable Q4_4a `"Q4_4a"'

label define Q4_4b 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q4_4b Q4_4b
label variable Q4_4b `"Q4_4b"'

label define Q4_4c 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q4_4c Q4_4c
label variable Q4_4c `"Q4_4c"'

label define Q4_4d 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q4_4d Q4_4d
label variable Q4_4d `"Q4_4d"'

label define Q6_0 1 `"Yes"' 0 `"No"' 
label values Q6_0 Q6_0
label variable Q6_0 `"Q6_0"'

label define Q6_7 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q6_7 Q6_7
label variable Q6_7 `"Q6_7"'

label define Q6_8 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q6_8 Q6_8
label variable Q6_8 `"Q6_8"'

label define Q6_9 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q6_9 Q6_9
label variable Q6_9 `"Q6_9"'

label define Q6_10 1 `"Chemical only"' 2 `"Organic only"' 3 `"Chemical & Organic"' 4 `"No use"' 
label values Q6_10 Q6_10
label variable Q6_10 `"Q6_10"'

label variable Q7_1_2__11 `"Q7_1_2:Cattle"'

label variable Q7_1_2__12 `"Q7_1_2:Buffaloes"'

label variable Q7_1_2__13 `"Q7_1_2:Sheep"'

label variable Q7_1_2__14 `"Q7_1_2:Goats"'

label variable Q7_1_2__15 `"Q7_1_2:Swine/ pigs"'

label variable Q7_1_2__16 `"Q7_1_2:Chickens"'

label variable Q7_1_2__17 `"Q7_1_2:Turkeys"'

label variable Q7_1_2__18 `"Q7_1_2:Geese"'

label variable Q7_1_2__19 `"Q7_1_2:Ducks"'

label variable Q7_1_2__20 `"Q7_1_2:Guinea fowls"'

label variable Q7_1_2__21 `"Q7_1_2:Quail"'

label variable Q7_1_2__22 `"Q7_1_2:Rabbits and hares"'

label variable Q7_1_2__23 `"Q7_1_2:Horses"'

label variable Q7_1_2__24 `"Q7_1_2:Asses"'

label variable Q7_1_2__25 `"Q7_1_2:Bees"'

label variable Q7_1_2__26 `"Q7_1_2:Silkworms"'

label variable Q7_1_2__99 `"Q7_1_2:Other animals"'

label define Q9_1 1 `"Yes"' 0 `"No"' 
label values Q9_1 Q9_1
label variable Q9_1 `"Q9_1"'

label variable Q9_4__11 `"Q9_4:4 wheel tractor"'

label variable Q9_4__12 `"Q9_4:2 wheel tractor"'

label variable Q9_4__13 `"Q9_4:Planting machine"'

label variable Q9_4__14 `"Q9_4:Tiller machines"'

label variable Q9_4__15 `"Q9_4:Seeder"'

label variable Q9_4__16 `"Q9_4:Knapsack sprayer"'

label variable Q9_4__17 `"Q9_4:Motorized sprayer"'

label variable Q9_4__18 `"Q9_4:Combined harvester"'

label variable Q9_4__19 `"Q9_4:Mechanized harvester"'

label variable Q9_4__20 `"Q9_4:Mechanized thresher with blower"'

label variable Q9_4__21 `"Q9_4:Mechanized thresher"'

label variable Q9_4__22 `"Q9_4:Winnowing machine"'

label variable Q9_4__23 `"Q9_4:Drying machines (grains/vegetables/fruits)"'

label variable Q9_4__24 `"Q9_4:Water pump (agriculture)"'

label variable Q9_4__25 `"Q9_4:Milking machine"'

label variable Q9_4__26 `"Q9_4:Milk coolers"'

label variable Q9_4__27 `"Q9_4:Meat cutting machines"'

label variable Q9_4__28 `"Q9_4:Grass cutter (For agricultural purpose)"'

label variable Q9_4__29 `"Q9_4:Tea leaf harvester"'

label variable Q9_4__30 `"Q9_4:Backhoe machines"'

label variable Q9_4__31 `"Q9_4:Other agricultural machines"'

label variable Q9_4__32 `"Q9_4:Instruments that use in aquaculture"'

label define Q10_1 1 `"Yes"' 0 `"No"' 
label values Q10_1 Q10_1
label variable Q10_1 `"Q10_1"'

label variable Q10_2_1a `"Q10_2_1a"'

label variable Q10_2_2a `"Q10_2_2a"'

label variable Q10_2_3a `"Q10_2_3a"'

label variable Q10_2_4a `"Q10_2_4a"'

label variable Q10_2_5a `"Q10_2_5a"'

label variable Q10_2_6a `"Q10_2_5a"'

label variable Q10_2_7a `"Q10_2_7a"'

label variable Q10_2_8a `"Q10_2_8a"'

label variable Q10_2_9a `"Q10_2_9a"'

label variable Q10_2_10a `"Q10_2_10a"'

label variable Q10_2_11a `"Q10_2_11a"'

label variable Q10_2_1b `"Q10_2_1b"'

label variable Q10_2_2b `"Q10_2_2b"'

label variable Q10_2_3b `"Q10_2_3b"'

label variable Q10_2_4b `"Q10_2_4b"'

label variable Q10_2_5b `"Q10_2_5b"'

label variable Q10_2_6b `"Q10_2_5b"'

label variable Q10_2_7b `"Q10_2_7b"'

label variable Q10_2_8b `"Q10_2_8b"'

label variable Q10_2_9b `"Q10_2_9b"'

label variable Q10_2_10b `"Q10_2_10b"'

label variable Q10_2_11b `"Q10_2_11b"'

label variable A16__Latitude `"A16: Latitude"'

label variable A16__Longitude `"A16: Longitude"'

label variable A16__Accuracy `"A16: Accuracy"'

label variable A16__Altitude `"A16: Altitude"'

label variable A16__Timestamp `"A16: Timestamp"'

label variable A20 `"A20"'
