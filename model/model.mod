set Courses;  # A subset of requirements
set Semesters ordered;
set Requirements;
set GradRequirements;  # A subset of Requirements

param prereqCourse{Courses, Requirements} binary;
param coreqCourse{Courses, Requirements} binary;
param coreqGroup{Requirements, Requirements} binary;
param reqCount{Requirements} >= 0;
param interest{Courses};
param credits{Courses};
param minSemesterCredits >= 0;
param maxSemesterCredits >= 0;
param highSemesterCredits >= 0; # number of non-overloaded credits considered "high" (15?)
param minGradCredits >= 0;
param isOffered{Courses, Semesters} binary;  # only allow core courses in the proper semesters
param creditPenalty >= 0; # amount of objective function penalty incurred for each "high" credit (over 15)
param fragilityPenalty >= 0;

var takeCourse{Courses, Semesters} binary;
var satisfied{Requirements, Semesters} binary;
var isHighCredits{Semesters} >= 0;

maximize Total_Interest:
    sum {s in Semesters, c in Courses} interest[c] * takeCourse[c, s]
    - sum{s in Semesters} (isHighCredits[s] * creditPenalty)
    - fragilityPenalty * sum{s in Semesters, c in Courses} interest[c] * isOffered[c, s] * (1 - sum{ss in Semesters: ss <= s} takeCourse[c, ss]);  # to be filled in

subject to Satisfaction{r in Requirements, s in Semesters}: # maybe there's a better name for this...
    reqCount[r] * satisfied[r, s] <=
        sum{rr in Requirements} (coreqGroup[rr,r] * satisfied[rr, s]) +  # Boolean logic
        sum{c in Courses} (prereqCourse[c, r] * credits[c] * sum{ss in Semesters: ss < s} takeCourse[c, ss]) +  # Prerequisite courses
        sum{c in Courses} (coreqCourse[c, r] * credits[c] * sum{ss in Semesters: ss <= s} takeCourse[c, ss]) +  # Corequisite courses
        reqCount[r] * (if s = first(Semesters) then 0 else satisfied[r, prev(s, Semesters)]);  # Satisfied requirements stay satisfied

subject to Graduation{r in GradRequirements}:
    satisfied[r, last(Semesters)] = 1;

subject to TotalCredits:
    sum{c in Courses, s in Semesters} credits[c] * takeCourse[c, s] >= minGradCredits;

subject to NoOverload{s in Semesters}:
    sum{c in Courses} credits[c] * takeCourse[c, s] <= maxSemesterCredits;

subject to HighCredits{s in Semesters}:
    (sum{c in Courses} credits[c] * takeCourse[c, s]) - isHighCredits[s] <= highSemesterCredits;

subject to FullTime{s in Semesters}:
    sum{c in Courses} credits[c] * takeCourse[c, s] >= minSemesterCredits;

subject to Prerequisites{c in Courses, s in Semesters}:
    takeCourse[c, s] <= isOffered[c, s] * satisfied[c, s];

subject to NoRepeats{c in Courses}:
    sum{s in Semesters} takeCourse[c, s] <= 1;
