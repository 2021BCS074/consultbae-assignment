# Data Issues Report (auto-generated from pipeline log)

Every issue below was actually caught by `merge.py` while running -- this file is generated from `ISSUES_LOG`, not written by hand.


## POSSIBLE_OVER_MERGE (2 occurrences)

- Cluster for {'Arjun Mehta'} was merged by name+city fallback but contains CONFLICTING identifiers -- phones={'9000000131', '9000000272'}, emails={'arjun.mehta77@mailtest.example.org', 'arjun.mehta9@example.in'}. This may be two different people with the same name in the same city, incorrectly merged. Left merged (no way to tell which is right from the data alone) but flagged here for manual review.
- Cluster for {'Nikhil Chopra'} was merged by name+city fallback but contains CONFLICTING identifiers -- phones={'9000000103'}, emails={'alt.nikhil.chopra70@example.com', 'nikhil.chopra70@example.com'}. This may be two different people with the same name in the same city, incorrectly merged. Left merged (no way to tell which is right from the data alone) but flagged here for manual review.

## blank_row (1 occurrences)

- source2 row 10 is entirely blank, dropped

## duplicate_row_same_source (1 occurrences)

- source1 row 29 ('Rohit Verma') has the same email as an earlier row ('R. Verma') -- likely the same person entered twice (e.g. name typo 'R. Verma' vs 'Rohit Verma'). Merged.

## embedded_duplicate_header (1 occurrences)

- source3 row 14 repeats the header row -- file is two exports concatenated together, dropped the extra header.

## match_email (17 occurrences)

- s1_0 <-> s2_9 matched on email 'tanvi.gupta31@example.com'
- s1_3 <-> s2_7 matched on email 'vikram.saxena60@example.com'
- s1_7 <-> s2_5 matched on email 'isha.chopra95@mailtest.example.org'
- s1_7 <-> s2_17 matched on email 'isha.chopra95@mailtest.example.org'
- s1_13 <-> s2_2 matched on email 'karan.bhatia32@mailtest.example.org'
- s1_15 <-> s2_3 matched on email 'arjun.mishra70@example.com'
- s1_16 <-> s2_6 matched on email 'meera.bhatia52@mailtest.example.org'
- s1_17 <-> s2_0 matched on email 'varun.jain29@example.com'
- s1_20 <-> s2_11 matched on email 'sneha.chopra99@example.in'
- s1_23 <-> s1_29 matched on email 'rohit.verma13@mailtest.example.org'
- s1_27 <-> s2_10 matched on email 'varun.saxena21@example.in'
- s1_28 <-> s2_13 matched on email 'gaurav.mehta79@mailtest.example.org'
- s1_31 <-> s2_12 matched on email 'deepak.nair44@example.com'
- s1_32 <-> s2_8 matched on email 'rahul.chopra70@example.com'
- s1_36 <-> s2_1 matched on email 'tanvi.agarwal97@example.in'
- s1_38 <-> s2_4 matched on email 'isha.kapoor54@example.com'
- s1_41 <-> s2_14 matched on email 'neha.bhatia60@mailtest.example.org'

## match_name_city (46 occurrences)

- s1_0 <-> s2_9 matched on name+city 'tanvi gupta|bengaluru'
- s1_0 <-> s3_19 matched on name+city 'tanvi gupta|bengaluru'
- s1_2 <-> s3_9 matched on name+city 'priya singh|gurugram'
- s1_3 <-> s2_7 matched on name+city 'vikram saxena|gurugram'
- s1_3 <-> s3_17 matched on name+city 'vikram saxena|gurugram'
- s1_5 <-> s3_7 matched on name+city 'sahil malhotra|noida'
- s1_6 <-> s3_8 matched on name+city 'shreya gupta|noida'
- s1_7 <-> s2_5 matched on name+city 'isha chopra|pune'
- s1_7 <-> s2_17 matched on name+city 'isha chopra|pune'
- s1_7 <-> s3_15 matched on name+city 'isha chopra|pune'
- s1_13 <-> s2_2 matched on name+city 'karan bhatia|noida'
- s1_13 <-> s3_12 matched on name+city 'karan bhatia|noida'
- s1_14 <-> s3_1 matched on name+city 'ritu sharma|noida'
- s1_15 <-> s2_3 matched on name+city 'arjun mishra|new delhi'
- s1_15 <-> s3_13 matched on name+city 'arjun mishra|new delhi'
- s1_17 <-> s2_0 matched on name+city 'varun jain|pune'
- s1_17 <-> s3_10 matched on name+city 'varun jain|pune'
- s1_18 <-> s2_15 matched on name+city 'arjun mehta|noida'
- s1_18 <-> s3_3 matched on name+city 'arjun mehta|noida'
- s1_18 <-> s3_25 matched on name+city 'arjun mehta|noida'
- ...and 26 more

## match_phone (27 occurrences)

- s1_0 <-> s3_19 matched on phone '...0254'
- s1_2 <-> s3_9 matched on phone '...0287'
- s1_3 <-> s3_17 matched on phone '...0113'
- s1_5 <-> s3_7 matched on phone '...0143'
- s1_6 <-> s3_8 matched on phone '...0227'
- s1_7 <-> s3_15 matched on phone '...0138'
- s1_10 <-> s3_5 matched on phone '...0260'
- s1_13 <-> s3_12 matched on phone '...0211'
- s1_14 <-> s3_1 matched on phone '...0146'
- s1_15 <-> s3_13 matched on phone '...0106'
- s1_16 <-> s3_16 matched on phone '...0223'
- s1_17 <-> s3_10 matched on phone '...0263'
- s1_18 <-> s3_3 matched on phone '...0131'
- s1_20 <-> s3_21 matched on phone '...0162'
- s1_21 <-> s3_6 matched on phone '...0116'
- s1_23 <-> s1_29 matched on phone '...0294'
- s1_25 <-> s1_35 matched on phone '...0103'
- s1_26 <-> s3_2 matched on phone '...0231'
- s1_27 <-> s3_20 matched on phone '...0170'
- s1_28 <-> s3_23 matched on phone '...0133'
- ...and 7 more

## shifted_columns (1 occurrences)

- source2 row 18 has columns shifted left by one (skill_tags ended up first): ['react, javascript, mysql', 'ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG', 'Isha Chopra', '1406/hr', 'Pune', 'active']. Repaired by rotating fields back.