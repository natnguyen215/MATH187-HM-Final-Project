from collections import namedtuple
from dataclasses import dataclass
import json
from typing import Collection, Dict, List, Optional, Set, Tuple, Union


@dataclass
class ReqGroup:
    name: str
    num: float
    groups: List["ReqGroup"]
    pre: List[str]
    co: List[str]


@dataclass
class Course:
    id: str
    credits: float
    offerings: Set[float]
    mudd_hum: bool
    hsa: bool
    writing: bool
    reqs: Optional[ReqGroup] = None


def noramlize_credits(credits: float, campus: str) -> float:
    return max(credits * (1 if campus == "HM" else 3), 0.1)  # Zero-credit courses are treated as 0.1 credits


def parse_identifier(department: str, courseNumber: int, suffix: str, affiliation: str, year: int, term: str, **kwarg) -> Tuple[str, float]:
    id = "%s%03d%s%s" % (department.ljust(4, "_"), courseNumber, suffix.ljust(2, "_"), affiliation)
    time = (year - (0 if term == "FA" else 0.5) - 23) % 4
    return id, time


def parse_course(identifier: Dict[str, Union[str, int]],
                 courseAreas: Collection[str],
                 credits: int,
                 **kwargs):
    id, time = parse_identifier(**identifier) # type: ignore
    return Course(id,
                  noramlize_credits(credits, id[9:11]),
                  {time, (time + 2) % 4},
                  "4HSA" in courseAreas,
                  "4HSS" in courseAreas,
                  "4WRT" in courseAreas)


LIMITED_COURSES = {
    "MATH019__HM": {0.0},
    "PHYS023__HM": {0.0},
    "WRIT001__HM": {0.0},
    "CSCI005__HM": {0.0},
    "CSCI042__HM": {0.0},
    "BIOL046__HM": {0.0, 0.5},
    "BIOL023__HM": {0.0, 0.5},
    "CHEM042__HM": {0.0, 0.5},
    "CHEM024__HM": {0.0, 0.5},
    "HSA_010__HM": {0.5},
    "MATH073__HM": {0.5},
    "PHYS024__HM": {0.5},
    "ENGR079__HM": {1.0},
    "PHYS050__HM": {1.0, 1.5},
    "CORE099__HM": {1.5},
    "ENGR004__HM": {0.0, 0.5, 1.0, 1.5},
    "BIOL182__HM": {2.0, 2.5, 3.0, 3.5},  # Biochemistry
    "BIOL191__HM": {2.0, 2.5, 3.0, 3.5},  # Bio Colloquium
    "BIOL193__HM": {3.0, 3.5},  # Bio Thesis
    "BIOL195__HM": {3.0, 3.5},  # Bio intensive research
    "CHEM151__HM": {3.0},  # Chem Thesis I
    "CHEM152__HM": {3.5},  # Chem Thesis II
    "CHEM199__HM": {2.0, 2.5, 3.0, 3.5},  # Chem Seminar
    "PHYS193__HM": {3.0},  # Physics Clinic I
    "PHYS194__HM": {3.5},  # Physics Clinic II
    "PHYS195__HM": {2.0, 2.5, 3.0, 3.5},  # Physics Colloquium
    "PHYS199__HM": {3.0, 3.5},  # Physics Thesis
    "MATH193__HM": {3.0, 3.5},  # Math Clinic
    "MATH197__HM": {3.0, 3.5},  # Math Thesis
    "MATH198__HM": {2.0, 2.5},  # Math Forum
    "CSMT183__HM": {3.0, 3.5},  # CS/Math Clinic I
    "CSMT184__HM": {3.0, 3.5},  # CS/Math Clinic II
    "CSCI183__HM": {3.0},  # CS Clinic I
    "CSCI184__HM": {3.5},  # CS Clinic II
    "CSCI195__HM": {2.0, 2.5, 3.0, 3.5},  # CS Colloquium
    "ENGR111__HM": {2.0, 2.5},  # Engineering Clinic I
    "ENGR112__HM": {3.0},  # Engineering Clinic II
    "ENGR113__HM": {3.5},  # Engineering Clinic III
    "ENGR122__HM": {2.0},  # Engineering Seminar
    "ENGR124__HM": {2.5},  # Engineering Seminar
    "MCBI199__HM": {2.0, 2.5, 3.0, 3.5},  # MCB Colloquium
}


def parse_jsons(*fnames: str) -> Dict[str, Course]:
    courses: Dict[str, Course] = {}
    for fname in fnames:
        print("Reading", fname)
        with open(fname, "rt", encoding="utf-8") as f:
            data = json.load(f)["json"]
        for datum in data:
            course = parse_course(**datum)
            if course.id in {"MATH168__HM", "PHYS024A_HM", "MATH055A_HM", "MATH199__HM", "CSCI042__HM"}: continue
            elif course.id.startswith("PE__"): continue
            if course.id in courses:
                courses[course.id] = Course(
                    course.id,
                    course.credits,
                    courses[course.id].offerings | course.offerings,
                    courses[course.id].mudd_hum and course.mudd_hum,
                    course.hsa,
                    courses[course.id].writing and course.writing
                )
            else:
                courses[course.id] = course
    for course in [*courses.values()]:
        if course.id in LIMITED_COURSES:
            course.offerings = LIMITED_COURSES[course.id]
        if course.id[4:6] == "19":
            courses[course.id + "2"] = Course(course.id + "2",
                                              course.credits,
                                              course.offerings.copy(),
                                              course.mudd_hum,
                                              course.hsa,
                                              course.writing,
                                              ReqGroup(course.id + "2",
                                                       course.credits,
                                                       [],
                                                       [course.id],
                                                       []))
            if course.id in LIMITED_COURSES:
                for i in range(3, len(LIMITED_COURSES[course.id]) + 1):
                    courses[course.id + str(i)] = Course(course.id + str(i),
                                                         course.credits,
                                                         course.offerings.copy(),
                                                         course.mudd_hum,
                                                         course.hsa,
                                                         course.writing,
                                                         ReqGroup(course.id + str(i),
                                                                  course.credits,
                                                                  [],
                                                                  [course.id + str(i-1)], []))
        if course.id in {"BIOL191__HM", "CHEM199__HM", "PHYS195__HM", "CSCI195__HM", "MCBI199__HM"}:
            courses[course.id + "3"] = Course(course.id + "3",
                                              course.credits,
                                              course.offerings.copy(),
                                              course.mudd_hum,
                                              course.hsa,
                                              course.writing,
                                              ReqGroup(course.id + "3", course.credits, [], [course.id + "2"], []))
            courses[course.id + "4"] = Course(course.id + "4",
                                              course.credits,
                                              course.offerings.copy(),
                                              course.mudd_hum,
                                              course.hsa,
                                              course.writing,
                                              ReqGroup(course.id + "4", course.credits, [], [course.id + "3"], []))
    for i in range(12):
        courses["STEM%03i__5C" % i] = Course("STEM%03i__5C" % i, 3, {n / 2 for n in range(0, 8, 1)}, False, False, False, None)
    for dept in ["BIOL", "CHEM", "PHYS", "MATH", "CSCI", "ENGR"]:
        for i in range(5):
            courses["%s9%02i__HM" % (dept, i)] = Course("%s9%02i__HM" % (dept, i), 3, {n / 2 for n in range(0, 8, 1)}, False, False, False, None)
    for i in range(10):
        courses["HSA_%03i__5C" % i] = Course("HSA_%03i__5C" % i, 3, {n / 2 for n in range(0, 8, 1)}, False, True, False, None)
    for i in range(4):
        courses["HSA_%03i__HM" % i] = Course("HSA_%03i__HM" % i, 3, {n / 2 for n in range(0, 8, 1)}, True, True, False, None)
    courses["HSA_100__HM"] = Course("HSA_100__HM", 3, {n / 2 for n in range(0, 8, 1)}, True, True, True, None)
    return courses


def write_courses(courses: Dict[str, Course], fname: str) -> None:
    with open(fname, "wt") as f:
        f.write(f"set Courses := {' '.join(id.replace(' ', '_') for id in courses)};\n")
        f.write("set Semesters := 0.0 0.5 1.0 1.5 2.0 2.5 3.0 3.5;\n")
        f.write("\n")
        f.write("param minSemesterCredits := 12;\n")
        f.write("param maxSemesterCredits := 18;\n")
        f.write("param highSemesterCredits := 15;\n")
        f.write("param minGradCredits := 120;\n")
        f.write("param creditPenalty := 1;\n")
        f.write("param fragilityPenalty := 0.05;\n")
        f.write("param credits :=\n")
        for course in courses.values():
            f.write(f"  {course.id} {course.credits}\n")
        f.write(";\n")
        f.write("param isOffered default 0 :=\n")
        for course in courses.values():
            f.write(f"  [{course.id},*]")
            for offering in course.offerings:
                f.write(f" {offering} 1")
            f.write("\n")
        f.write(";\n")


if __name__ == "__main__":
    from sys import argv
    if len(argv) <= 2:
        print(f"Usage {argv[0]} <dat file> <json files> ...")
    write_courses(parse_jsons(*argv[2:]), argv[1])
