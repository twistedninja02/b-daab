-- B-DAAB Sample Data
-- Matches expected_result values in data/tasks.json

-- Hospitals (q001: SELECT * FROM hospitals)
INSERT INTO hospitals VALUES (1, 'Dhaka Medical Hospital',  'Dhaka');
INSERT INTO hospitals VALUES (2, 'Sylhet MAG Ospeital',     'Sylhet');
INSERT INTO hospitals VALUES (3, 'Chittagong Hospital',     'Chittagong');
INSERT INTO hospitals VALUES (4, 'Khulna General Hospital', 'Khulna');
INSERT INTO hospitals VALUES (5, 'Rajshahi Medical Center', 'Rajshahi');

-- Patients (q002: COUNT(*) = 10, q003: per-hospital counts)
-- Dhaka Medical Hospital (id=1): 3 patients
INSERT INTO patients VALUES (1,  'Rahim Uddin',    1);
INSERT INTO patients VALUES (2,  'Karim Sheikh',   1);
INSERT INTO patients VALUES (3,  'Nadia Islam',    1);
-- Sylhet MAG Ospeital (id=2): 3 patients
INSERT INTO patients VALUES (4,  'Jamal Hossain',  2);
INSERT INTO patients VALUES (5,  'Ruma Begum',     2);
INSERT INTO patients VALUES (6,  'Farhan Ahmed',   2);
-- Chittagong Hospital (id=3): 2 patients
INSERT INTO patients VALUES (7,  'Sadia Akter',    3);
INSERT INTO patients VALUES (8,  'Mizanur Rahman', 3);
-- Khulna General Hospital (id=4): 0 patients (no inserts)
-- Rajshahi Medical Center (id=5): 2 patients
INSERT INTO patients VALUES (9,  'Taslima Khanam', 5);
INSERT INTO patients VALUES (10, 'Sabbir Khan',    5);

-- Schools (q004: SELECT * FROM schools, q005: COUNT WHERE city='Dhaka' = 1)
INSERT INTO schools VALUES (1, 'Dhaka School',      'Dhaka');
INSERT INTO schools VALUES (2, 'Sylhet School',     'Sylhet');
INSERT INTO schools VALUES (3, 'Chittagong School', 'Chittagong');
INSERT INTO schools VALUES (4, 'Khulna School',     'Khulna');
INSERT INTO schools VALUES (5, 'Rajshahi School',   'Rajshahi');

-- Students
INSERT INTO students VALUES (1,  'Arif Hasan',      1);
INSERT INTO students VALUES (2,  'Mitu Akter',      1);
INSERT INTO students VALUES (3,  'Rubel Mia',       2);
INSERT INTO students VALUES (4,  'Shapna Begum',    2);
INSERT INTO students VALUES (5,  'Tanvir Ahmed',    3);
INSERT INTO students VALUES (6,  'Sumaiya Islam',   4);
INSERT INTO students VALUES (7,  'Naim Hossain',    5);

-- Shops
INSERT INTO shops VALUES (1, 'Dhaka Electronics',  'Rahim Traders',  'Dhaka');
INSERT INTO shops VALUES (2, 'Sylhet Cloth House', 'Kamal Uddin',    'Sylhet');
INSERT INTO shops VALUES (3, 'CTG Furniture',      'Nasrin Begum',   'Chittagong');

-- Products
INSERT INTO products VALUES (1, 'LED TV',       1, 35000.00);
INSERT INTO products VALUES (2, 'Refrigerator', 1, 42000.00);
INSERT INTO products VALUES (3, 'Saree',        2,  1200.00);
INSERT INTO products VALUES (4, 'Panjabi',      2,   800.00);
INSERT INTO products VALUES (5, 'Wooden Chair', 3,  3500.00)
