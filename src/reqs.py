import re
from typing import Dict, List, Optional, Union

from parsejson import Course, ReqGroup, parse_jsons


debug = False
course_re = r"(?P<dept>[A-Z]{2,4}) ?(?P<code>[0-9]{3})(?P<suffix>[A-Z]{0,2}) ?(?P<campus>[A-Z]{2}(/[A-Z]{2})*)"


def normalize_id(m: Optional[re.Match], courses: Dict[str, Course]):
    if m is None:
        return []
    return list(filter(lambda c: c in courses, [
        (("CSCI" if m.group("dept") == "CS" else m.group("dept").ljust(4)) +
        m.group("code") + m.group("suffix").ljust(2) + campus).replace(" ", "_")
        for campus in m.group("campus").split("/")
    ]))


def parse_reqs(expr: str, name: str, courses: Dict[str, Course], co: bool=False) -> Optional[ReqGroup]:
    regex = "|".join([
        f"(?P<id>{course_re})",
        r"(?P<or>\W(or|OR|Or)\W)",
        r"(?P<and>\W(and|AND|And)\W)",
        r"(?P<open>[(])",
        r"(?P<close>[)])",
        r"(?P<misc>[a-z]|$)"
    ])
    root = ReqGroup(name, 0, [], [], [])
    trail = [root]
    for m in re.finditer(regex, expr):
        if debug: print(m.lastgroup, end="|")
        if m.lastgroup == "misc" or m.lastgroup == "close":
            group = trail.pop()
            if group.num <= 0:
                group.num = len(group.groups)
                group.num += sum(courses[course].credits for course in group.pre)
                group.num += sum(courses[course].credits for course in group.co)
            if not group.pre and not group.co and len(group.groups) == 1:
                group.num = group.groups[0].num
                group.pre = group.groups[0].pre
                group.co = group.groups[0].co
                group.groups = group.groups[0].groups
            if not trail:
                break
        elif m.lastgroup == "open":
            new_group = ReqGroup(f"{trail[-1].name}_{len(trail[-1].groups)}", 0, [], [], [])
            trail[-1].groups.append(new_group)
            trail.append(new_group)
        elif m.lastgroup == "and":
            trail[-1].num = 0
        elif m.lastgroup == "or":
            trail[-1].num = 0.1
        elif m.lastgroup == "id":
            course = normalize_id(m, courses)
            if len(course) <= 1 or trail[-1].num == 0.1:
                if co:
                    trail[-1].co.extend(course)
                else:
                    trail[-1].pre.extend(course)
            else:
                if co:
                    trail[-1].groups.append(ReqGroup(f"{trail[-1].name}_{len(trail[-1].groups)}", 0.1, [], [], course))
                else:
                    trail[-1].groups.append(ReqGroup(f"{trail[-1].name}_{len(trail[-1].groups)}", 0.1, [], course, []))
    if debug: print(";")
    if trail:
        print(f"Uh oh! Course '{name}' has items remaining on the requisites stack.")
    if root.num == 0:
        return None
    return root


def parse_files(courses: Dict[str, Course], *fnames: str) -> None:
    for fname in fnames:
        print("Processing", fname)
        with open(fname, "rt") as f:
            course = ""
            for line in f:
                if line.startswith("Course: "):
                    course = normalize_id(re.match(course_re, line[8:]), courses)
                    if debug: print(f"Found course '{course}'")
                    course = course[0] if course else ""
                    if course in courses and courses[course].reqs is not None:
                        course = ""
                elif course not in courses:
                    continue
                elif line.startswith("Prerequisite"):
                    new_req = parse_reqs(line[17:], course, courses, False)
                    old_req = courses[course].reqs
                    if new_req is not None and old_req is not None:
                        new_req.name += "_pre"
                        old_req.name += "_co"
                        courses[course].reqs = ReqGroup(course, 2, [old_req, new_req], [], [])
                    else:
                        courses[course].reqs = old_req or new_req
                    print(".", end="")
                elif line.startswith("Corequisite"):
                    new_req = parse_reqs(line[16:], course, courses, True)
                    old_req = courses[course].reqs
                    if new_req is not None and old_req is not None:
                        new_req.name += "_co"
                        old_req.name += "_pre"
                        courses[course].reqs = ReqGroup(course, 2, [old_req, new_req], [], [])
                    else:
                        courses[course].reqs = old_req or new_req
                    print("-", end="")
        print("", end="\n")


def write_reqs(fname: str, *reqs: ReqGroup, courses: Dict[str, Course]) -> None:
    with open(fname, "wt") as f:
        f.write("set Requirements :=\n ")
        for req in reqs:
            f.write(f" {req.name}")
        for course in courses.values():
            if course.reqs is None or course.reqs.num == 0:
                f.write(f" {course.id}")
        f.write(";\n\n")
        f.write("param reqCount default 0 :=\n")
        for req in reqs:
            f.write(f"  {req.name} {req.num}\n")
        f.write(";\n")
        f.write("param prereqCourse default 0 :=\n")
        for req in reqs:
            if not req.pre: continue
            f.write(f"  [*,{req.name}]")
            for course in req.pre:
                f.write(f" {course} 1")
            f.write("\n")
        f.write(";\n")
        f.write("param coreqCourse default 0 :=\n")
        for req in reqs:
            if not req.co: continue
            f.write(f"  [*,{req.name}]")
            for course in req.co:
                f.write(f" {course} 1")
            f.write("\n")
        f.write(";\n")
        f.write("param coreqGroup default 0 :=\n")
        for req in reqs:
            if not req.groups: continue
            f.write(f"  [*,{req.name}]")
            for group in req.groups:
                f.write(f" {group.name} 1")
            f.write("\n")
        f.write(";\n")


def get_majors_reqs(courses: Dict[str, Course]) -> Dict[str, ReqGroup]:
    def And(name: str, *data: Union[ReqGroup, str]) -> ReqGroup:
        pres = [c.replace(" ", "_") for c in data if isinstance(c, str)]
        subs = [g for g in data if isinstance(g, ReqGroup)]
        queue = subs[:]
        while queue:
            curr = queue.pop()
            curr.name = name + "_" + curr.name
            queue.extend(curr.groups)
        return ReqGroup(name, sum(courses[c].credits for c in pres) + len(subs), subs, [], pres)
    
    def Or(name: str, *data: Union[ReqGroup, str]) -> ReqGroup:
        pres = [c.replace(" ", "_") for c in data if isinstance(c, str) and c.replace(" ", "_") in courses]
        subs = [g for g in data if isinstance(g, ReqGroup)]
        queue = subs[:]
        while queue:
            curr = queue.pop()
            curr.name = name + "_" + curr.name
            queue.extend(curr.groups)
        return ReqGroup(name, 0.1, subs, [], pres)
    
    def AtLeast(name: str, num: float, *data: Union[ReqGroup, str]) -> ReqGroup:
        pres = [c.replace(" ", "_") for c in data if isinstance(c, str) and c.replace(" ", "_") in courses]
        subs = [g for g in data if isinstance(g, ReqGroup)]
        queue = subs[:]
        while queue:
            curr = queue.pop()
            curr.name = name + "_" + curr.name
            queue.extend(curr.groups)
        return ReqGroup(name, num, subs, [], pres)
    
    majors = {
    "Math & CS": And("Maj_MathCS",
        "MATH055  HM",
        Or("IntroCS", "CSCI060  HM", "CSCI042  HM"),
        "CSCI081  HM",
        Or("Algs", "CSCI140  HM", "MATH168  HM"),
        "CSCI070  HM",
        "MATH062  HM",
        "MATH082  HM",
        "MATH131  HM",
        "MATH171  HM",
        AtLeast("CSElec", 6, "ENGR085A HM", "ENGR151  HM", "ENGR155  HM", "ENGR158  HM", "ENGR161  HM", "MCBI118B HM", "BIOL188  HM", "PHYS084  HM", "PHYS170  HM", "PSYC183  SC", "CHEM80  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI123  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM", *("CSCI90%i__HM" for i in range(5))),
        AtLeast("MathElec", 6, "MATH104  HM", "MATH106  HM", "MATH119  HM", "MATH127  HM",  "MATH132  HM", "MATH136  HM", "MATH137  HM", "MATH138  HM", "MATH142  HM", "MATH143  HM", "MATH147  HM", "MATH152  HM", "MATH153  HM", "MATH155  HM", "MATH156  HM", "MATH157  HM", "MATH158  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH172  HM", "MATH173  HM", "MATH174  HM", "MATH175  HM", "MATH176  HM", "MATH178  HM", "MATH188  HM", "MATH187  HM", "MATH184  HM", "MATH181  HM", "MATH179  HM", "MATH189  HM", "MCBI117  HM", *("MATH90%i__HM" for i in range(5))),
        "CSCI195  HM",
        "CSCI195  HM2",
        "MATH198  HM",
        "CSMT183  HM",
        "CSMT184  HM"
    ),
    "CS": And("Maj_CS",
        Or("CSCore", "CSCI060  HM", "CSCI042  HM"),
        "MATH055  HM",
        "CSCI081  HM",
        "CSCI070  HM",
        "CSCI105  HM",
        "CSCI123  HM",
        "CSCI140  HM",
        AtLeast("CSElec", 9, "MATH104  HM", "MATH106  HM", "MATH157  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH187  HM", "ENGR085A HM", "ENGR151  HM", "ENGR155  HM", "ENGR158  HM", "ENGR161  HM", "MCBI118A HM", "MCBI118B HM", "BIOL188  HM", "PHYS084  HM", "PHYS170  HM", "PSYC183  SC", "CHEM80  HM", "MCBI117  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI181  HM", *("CSCI90%i__HM" for i in range(5))),  
        And("CSColloquium", "CSCI195  HM", "CSCI195  HM2", "CSCI195  HM3", "CSCI195  HM4"),
        "CSCI183  HM",
        "CSCI184  HM"
    ),
    "Physics": And("Maj_Phys",
        "MATH082  HM",
        "PHYS051  HM",
        "PHYS052  HM",
        "PHYS054  HM",
        "PHYS064  HM",
        "PHYS111  HM",
        "PHYS116  HM",
        "PHYS133  HM",
        "PHYS134  HM",
        "PHYS151  HM",
        And("PhysColloquium", "PHYS195  HM", "PHYS195  HM2", "PHYS195  HM3", "PHYS195  HM4"),
        Or("Thesis", And("Clinic", "PHYS193  HM", "PHYS194  HM"), And("PhysThesis", "PHYS199  HM", )) 
    ),
    "Chemistry": And("Maj_Chem",
        "CHEM051  HM",
        "CHEM056  HM",
        "CHEM103  HM",
        "CHEM104  HM",
        "CHEM182  HM",
        "PHYS051  HM",
        Or("Math", "BIOL154  HM", "MATH056  HM", "MATH062  HM", "MATH082  HM"),
        AtLeast("ChemLab", 4, "CHEM053  HM", "CHEM058  HM", "CHEM109  HM", "CHEM110  HM", "CHEM184  HM"),
        AtLeast("CHEMElec", 8, "CHEM047  HM", "CHEM048  HM", "CHEM080  HM", "CHEM105  HM", "CHEM106  HM", "CHEM111  HM", "CHEM112  HM", "CHEM114  HM", "CHEM116  HM", "CHEM122  HM", "CHEM161  HM", "CHEM163  HM", "CHEM164  HM", "CHEM165  HM", "CHEM166  HM", "CHEM167  HM", "CHEM168  HM", "CHEM170  HM", "CHEM171  HM", "CHEM173  HM", "CHEM187  HM", "CHEM189  HM", "CHEM190  HM", "CHEM192  HM", "CHEM194  HM", "CHEM195  HM", "CLES101  HM", *("CHEM90%i__HM" for i in range(5))), 
        And("ChemSeminar", "CHEM199  HM", "CHEM199  HM2", "CHEM199  HM3", "CHEM199  HM4"),
        Or("ThesisOrClinic", And("Thesis", "CHEM151  HM", "CHEM152  HM"), And("Clinic", "ENGR112  HM", "ENGR113  HM"))
    ),
    "Biology": And("Maj_Bio",
        "BIOL054  HM",
        "BIOL154  HM",
        "BIOL101  HM",
        "BIOL108  HM",
        "BIOL109  HM",
        "BIOL113  HM",
        "CHEM056  HM",
        "CHEM058  HM",
        "CHEM105  HM",
        Or("BioLab", And("WithBioChem", "BIOL184  HM", Or("Other", "BIOL103  HM", "BIOL110  HM", "BIOL111  HM")), AtLeast("NoBioChem", 4, "BIOL103  HM", "BIOL110  HM", "BIOL111  HM")),
        Or("BioSeminar", "BIOL121  HM", "BIOL129  HM", "BIOL183  HM", "BIOL185  HM", "BIOL189  HM"),
        AtLeast("BioElecs", 26, "BIOL197__HM", "BIOL190B_HM", *(c.id for c in courses.values() if (c.id.startswith("BIOL1") or c.id.startswith("MCBI1")) and c.id[5] != "9"), *("BIOL90%i__HM" for i in range(5))),
        And("BioColloquium", "BIOL191  HM", "BIOL191  HM2", "BIOL191  HM3", "BIOL191  HM4"),
        Or("ThesisOrClinic", And("BioThesis", "BIOL193  HM", "BIOL193  HM2"), And("IntensiveBioThesis", "BIOL195  HM", "BIOL195  HM2"), And("CSClinic", "CSCI183  HM", "CSCI184  HM"), AtLeast("EngrClinic", 6, "ENGR111  HM", "ENGR112  HM", "ENGR113  HM"), And("PhysClinic", "PHYS193  HM", "PHYS194  HM"), And("MathClinic", "MATH193  HM", "MATH193  HM2"))
    ),
    "Molecular Biology": And("Maj_MolBio",
        "BIOL054  HM",
        "BIOL154  HM",
        "BIOL101  HM",
        "BIOL108  HM",
        "BIOL109  HM",
        "BIOL111  HM",
        "BIOL113  HM",
        "BIOL182  HM",
        "CHEM056  HM",
        "CHEM058  HM",
        "CHEM105  HM",
        "CHEM111  HM",
        Or("MolBio", "BIOL122  HM", "BIOL160  HM"),
        Or("BioLab", "BIOL103  HM", "BIOL110  HM", "BIOL184  HM"),
        Or("SeminarCourse", "BIOL121  HM", "BIOL129  HM", "BIOL183  HM", "BIOL185  HM", "BIOL189  HM"),
        AtLeast("BioElecs", 26, "BIOL197__HM", "BIOL190B_HM", *(c.id for c in courses.values() if (c.id.startswith("BIOL1") or c.id.startswith("MCBI1")) and c.id[5] != "9"), *("BIOL90%i__HM" for i in range(5))),
        AtLeast("Colloquium", 0.4, "BIOL191  HM", "CHEM199  HM"),
        Or("Capstone", AtLeast("BioThesis", 6, "BIOL193  HM"), AtLeast("IntensiveResearch", 12, "BIOL195  HM"), And("ChemThesis", "CHEM151  HM", "CHEM152  HM"), And("CSClinic", "CSCI183  HM", "CSCI184  HM"), AtLeast("EngrClinic", 6, "ENGR111  HM", "ENGR112  HM", "ENGR113  HM"), AtLeast("MathClinic", 6, "MATH193  HM"), And("PhysClinic", "PHYS193  HM", "PHYS194  HM"))
    ),
    "Math": And("Maj_Math",
        "MATH055  HM",
        Or("Computational", "CSCI081  HM", "CSCI142  HM", "MATH164  HM", "MATH165  HM", "CSCI140  HM"),
        "MATH062  HM",
        "MATH082  HM",
        "MATH131  HM",
        "MATH171  HM",
        "MATH180  HM",
        AtLeast("MathElec", 7, "MCBI199  hm", "MCBI118B HM", "MCBI118A HM", "MCBI117  HM", "MATH104  HM", "MATH106  HM", "MATH119  HM", "MATH127  HM",  "MATH132  HM", "MATH136  HM", "MATH137  HM", "MATH138  HM", "MATH142  HM", "MATH143  HM", "MATH147  HM", "MATH152  HM", "MATH153  HM", "MATH155  HM", "MATH156  HM", "MATH157  HM", "MATH158  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH172  HM", "MATH173  HM", "MATH174  HM", "MATH175  HM", "MATH176  HM", "MATH178  HM", "MATH188  HM", "MATH187  HM", "MATH184  HM", "MATH181  HM", "MATH179  HM", "MATH189  HM", *("MATH90%i__HM" for i in range(5))), 
        "MATH198  HM",
        Or("ThesisOrClinic", And("MathThesis", "MATH193  HM", "MATH193  HM2"),  And("BioThesis", "MATH197  HM", "MATH197  HM2"))
    ),
    "Engineering": And("Maj_Engr",
        "ENGR004  HM",
        "ENGR079  HM",
        "ENGR082  HM",
        "ENGR083  HM",
        "ENGR084  HM",
        "ENGR085  HM",
        "ENGR086  HM",
        "ENGR072  HM",
        "MATH056  HM",
        "ENGR101  HM",
        "ENGR102  HM",
        "ENGR080  HM",
        "ENGR111  HM",
        "ENGR112  HM",
        "ENGR113  HM",
        "ENGR122  HM",
        "ENGR124  HM",
        AtLeast("EngrElec", 9, "ENGR131  HM", "ENGR132  HM", "ENGR133  HM", "ENGR134  HM", "ENGR138  HM", "ENGR147  HM", "ENGR151  HM", "ENGR154  HM", "ENGR155  HM", "ENGR157  HM", "ENGR164  HM", "ENGR168  HM", "ENGR171  HM", "ENGR172  HM", "ENGR175  HM", "ENGR176  HM", "ENGR177  HM", "ENGR178  HM", "ENGR180  HM", "ENGR181  HM", "ENGR182  HM", "ENGR183  HM", "ENGR185A HM", "ENGR185B HM", "ENGR186  HM", "ENGR187  HM", "ENGR188  HM", "ENGR189  HM", "ENGR205  HM", "ENGR206  HM", "ENGR207  HM" , "ENGR208  HM", "ENGR240  HM", "ENGR278  HM", "CSCI70  HM", *("ENGR90%i__HM" for i in range(5)))
    ),
    "Biology & Climate": And(
        "Maj_BioClim",
        "BIOL054  HM",
        "BIOL154  HM",
        "BIOL108  HM",
        "BIOL110  HM",
        Or("BioGroup", "BIOL101  HM", "BIOL109  HM", "BIOL113  HM"),
        Or("BioSeminar", "BIOL121  HM", "BIOL129  HM", "BIOL183  HM", "BIOL185  HM", "BIOL189  HM"),
        AtLeast("BioElec", 3, "BIOL197__HM", "BIOL190B_HM", *(c.id for c in courses.values() if (c.id.startswith("BIOL1") or c.id.startswith("MCBI1")) and c.id[5] != "9" and c.id not in {"BIOL101  HM", "BIOL109  HM", "BIOL113  HM", "BIOL121  HM", "BIOL129  HM", "BIOL183  HM", "BIOL185  HM", "BIOL189  HM", "BIOL154  HM", "BIOL108  HM", "BIOL110  HM"}), *("BIOL90%i__HM" for i in range(5))),
        Or("Thermodynamics", "CHEM051  HM", "ENGR082  HM", "PHYS117  HM"),
        Or("BioComputational", "CSCI144  HM", "CHEM080  HM", "MATH164  HM", "PHYS064  HM"),
        Or("BioClimateElective", "MATH082  HM", "MATH102  PZ", "MATH102  PO", "MATH102  SC", "MATH111  CMC", "PHYS051  HM", "PHYS034L  KS"),
        "CLES101  HM",
        "CLES131  HM",
        Or("ClimateInterventions", AtLeast("ClimateInterventionCredits", 3, "CHEM192  HM", "CLES122  HM", "CLES130  HM", "CHEM192  HM2"), And("Justice", "CLES121  HM", "CLES122  HM")),
        Or("ClimateContexts", And("Justice", "CLES121  HM", "CLES122  HM"), "CLES130  HM", "CLES131  HM", "CHEM170  HM", "ENGR138  HM"),
        Or("ClimateStats", "MATH056  HM", "MATH062  HM", "MATH052  CM", "MATH052  PZ", "MATH057  PO", "MATH058  PO", "MATH151  PO", "MATH152  PO", "PHYS117  HM", "BIOL154  HM"),
        And("BioColloqium", "BIOL191  HM", "BIOL191  HM2"),
        And("ClimateColloqium", "CLES199  HM", "CLES199  HM2"),
        Or("BioClimateCapstone", And("Thesis", "BIOL193  HM", "BIOL193  HM2"), And("CSClinic", "CSCI183  HM","CSCI184  HM"), And("EngClinic", "ENGR112  HM", "ENGR113  HM"), And("MathClinic", "MATH193  HM", "MATH193  HM2"), And("PhysClinic", "PHYS193  HM", "PHYS194  HM"))
    ),
    "Chemistry & Biology": And(
        "Maj_BioChem",
        "CHEM051  HM",
        "CHEM056  HM",
        "CHEM105  HM",
        "BIOL054  HM",
        "BIOL154  HM", 
        "BIOL111  HM",
        "BIOL113  HM",
        Or("ChemWithoutCells", "CHEM103  HM", "CHEM104  HM"),
        Or("BioChem", "BIOL182  HM", "CHEM182  HM"),
        Or("Topics", "BIOL189  HM", "CHEM189  HM"),
        "CHEM058  HM",
        Or("BioChemLab", "BIOL184  HM", "CHEM184  HM"),
        AtLeast("ChemLab", 2, "CHEM053  HM", "CHEM109  HM", "CHEM110  HM", "CHEM111  HM"),
        Or("OrganicBio", "BIOL101  HM", "BIOL108  HM", "BIOL109  HM"),
        AtLeast("BioElective", 3, "BIOL197__HM", "BIOL190B_HM", *(c.id for c in courses.values() if (c.id.startswith("BIOL1") or c.id.startswith("MCBI1")) and c.id[5] != "9" and c.id not in {"BIOL101  HM", "BIOL154  HM", "BIOL111  HM", "BIOL113  HM", "BIOL182  HM", "BIOL189  HM", "BIOL184  HM", "BIOL108  HM", "BIOL109  HM"}), *("BIOL90%i__HM" for i in range(5))),        And("BioColloqium", "BIOL191  HM", "BIOL191  HM2"),
        And("ChemColloqium", "CHEM199  HM", "CHEM199  HM2"),
        Or("Capstone", And("BioThesis", "BIOL193  HM", "BIOL193  HM2"), And("BioResearch", "BIOL195  HM", "BIOL195  HM2"), And("ChemThesis", "CHEM151  HM", "CHEM152  HM"), And("EngrClinic", "ENGR112  HM", "ENGR113  HM"))
    ),
    "Chemistry & Climate": And("Maj_ChemClimate",
        "CHEM051  HM",
        "CHEM056  HM",
        "CHEM103  HM",
        "CHEM109  HM",
        Or("Or1", "CHEM053  HM", "CHEM058  HM", "CHEM110  HM", "CHEM112  HM", "CHEM184  HM"),
        AtLeast("ChemClass", 6, "CHEM047  HM", "CHEM048  HM", "CHEM080  HM", "CHEM105  HM", "CHEM106  HM", "CHEM111  HM", "CHEM112  HM", "CHEM114  HM", "CHEM116  HM", "CHEM122  HM", "CHEM161  HM", "CHEM163  HM", "CHEM164  HM", "CHEM165  HM", "CHEM166  HM", "CHEM167  HM", "CHEM168  HM", "CHEM170  HM", "CHEM171  HM", "CHEM173  HM", "CHEM187  HM", "CHEM189  HM", "CHEM190  HM", "CHEM192  HM", "CHEM193  HM", "CHEM194  HM", "CHEM195  HM", *("CHEM90%i__HM" for i in range(4))), # Hacked for double counts
        AtLeast("ChemUpperDiv", 3, "CHEM105  HM", "CHEM106  HM", "CHEM111  HM", "CHEM112  HM", "CHEM114  HM", "CHEM116  HM", "CHEM122  HM", "CHEM161  HM", "CHEM163  HM", "CHEM164  HM", "CHEM165  HM", "CHEM166  HM", "CHEM167  HM", "CHEM168  HM", "CHEM170  HM", "CHEM171  HM", "CHEM173  HM", "CHEM187  HM", "CHEM189  HM", "CHEM190  HM", "CHEM192  HM", "CHEM193  HM", "CHEM194  HM", "CHEM195  HM", "CHEM904"),
        "PHYS051  HM",
        "MATH082  HM",
        AtLeast("ChemClimateProbStats", 3, "MATH056  HM", "MATH062  HM", "PHYS117  HM", "BIOL154  HM"),
        AtLeast("ChemClimateComputational", 3, "CHEM080  HM","PHYS064  HM", "CSCI144  HM","MATH164  HM"),
        "CLES101  HM",
        "CHEM170  HM",
        Or("ClimateInterventions", AtLeast("ClimateInterventionCredits", 3, "CHEM192  HM", "CLES122  HM", "CLES130  HM", "CHEM192  HM2"), And("Justice", "CLES121  HM", "CLES122  HM")),
        Or("ClimateContexts", And("Justice", "CLES121  HM", "CLES122  HM"), "CLES130  HM", "CLES131  HM", "CHEM170  HM", "ENGR138  HM"),
        And("ChemSeminar", "CHEM199  HM", "CHEM199  HM2"),
        And("ClimateColloqium", "CLES199  HM", "CLES199  HM2"),
        "CHEM151  HM",
        "CHEM152  HM"
    ),
    "CS & Physics": And("Maj_CsPhys",
        Or("IntroCS", "CSCI060  HM", "CSCI042  HM" ),
        "CSCI070  HM",
        Or("CSCoreElective", "CSCI081  HM", "CSCI105  HM"), 
        "CSCI140  HM",
        AtLeast("CSElective", 6, "CSCI081  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI123  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM", *("CSCI0%i__HM" for i in range(5))),
        AtLeast("CSColloqium", 0.2, "CSCI195  HM"),
        "MATH055  HM",
        "MATH082  HM",
        "PHYS051  HM",
        "PHYS052  HM", 
        "PHYS054  HM",
        "PHYS064  HM",
        Or("Quantum","PHYS084  HM", "PHYS116  HM"),
        "PHYS111  HM",
        "PHYS117  HM",
        Or("Lab", "PHYS133  HM", "PHYS134  HM"),
        And("PhysColloqium", "PHYS195  HM", "PHYS195  HM2"),
        AtLeast("PhysCSElective", 9, "PHYS170X  HM", "CSCI081  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI123  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM", *("CSCI0%i__HM" for i in range(5))),
        Or("Capstone", And("CSMTClinic", "CSMT183  HM", "CSMT184  HM"), And("PhysClinic", "PHYS193  HM", "PHYS194  HM"), And("PhysThesis", "PHYS199  HM", "PHYS199  HM2"))
    ),
    "Math & Physics": And(
        "Maj_MathPhys",
        "MATH055  HM",
        "MATH082  HM",
        "MATH131  HM",
        "MATH157  HM",
        "MATH171  HM",
        "MATH180  HM",
        "MATH198  HM",
        "PHYS051  HM",
        "PHYS052  HM",
        "PHYS054  HM",
        "PHYS111  HM",
        "PHYS116  HM",
        "PHYS117  HM",
        "PHYS134  HM",
        Or("Fields", "PHYS151  HM", "PHYS154  HM", "PHYS156  HM"),
        And("PhysColloquium", "PHYS195  HM", "PHYS195  HM2"),
        Or("ScientificComp", "MATH164  HM", "MATH165  HM", "PHYS170  HM"),
        Or("ThesisOrClinic", And("PhysThesis", "PHYS199  HM", "PHYS199  HM2"), And("MathThesis", "MATH197  HM", "MATH197  HM2"), And("PhysClinic", "PHYS193  HM", "PHYS194  HM"), And("MathClinic", "MATH193  HM", "MATH193  HM2"))
    ),
    "Mathematical and Computational Biology": And(
        "Maj_MathCompBio",
        "BIOL054  HM",
        "BIOL154  HM",
        "MATH055  HM",
        "MATH082  HM",
        "MCBI118A HM",
        "MCBI118B HM",
        AtLeast("BioFoundations", 6, "BIOL101  HM", "BIOL108  HM", "BIOL109  HM", "BIOL113  HM"),
        Or("BioLab", "BIOL103  HM", "BIOL110  HM", "BIOL111  HM", "BIO184  HM"),
        Or("BioSeminar", "BIOL121  HM", "BIOL129  HM", "BIOL183  HM", "BIOL185  HM", "BIOL189  HM"),
        Or("AdvancedBio", "BIOL119  HM", "MATH119  HM", "BIOL188  HM"),
        AtLeast("MathElec", 3, "MATH104  HM", "MATH106  HM", "MATH119  HM", "MATH127  HM",  "MATH132  HM", "MATH136  HM", "MATH137  HM", "MATH138  HM", "MATH142  HM", "MATH143  HM", "MATH147  HM", "MATH152  HM", "MATH153  HM", "MATH155  HM", "MATH156  HM", "MATH157  HM", "MATH158  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH168  HM", "MATH172  HM", "MATH173  HM", "MATH174  HM", "MATH175  HM", "MATH176  HM", "MATH178  HM", "MATH188  HM", "MATH187  HM", "MATH184  HM", "MATH181  HM", "MATH179  HM", "MATH189  HM", *("MATH90%i__HM" for i in range(5))),
        AtLeast("CSElec", 3, "CSCI60  HM", "CSCI70  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI140  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI123  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM"),  
        AtLeast("MathOrCSElec", 11,  "CSCI60  HM", "CSCI70  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI140  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI123  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM", "MATH104  HM", "MATH106  HM", "MATH119  HM", "MATH127  HM",  "MATH132  HM", "MATH136  HM", "MATH137  HM", "MATH138  HM", "MATH142  HM", "MATH143  HM", "MATH147  HM", "MATH152  HM", "MATH153  HM", "MATH155  HM", "MATH156  HM", "MATH157  HM", "MATH158  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH168  HM", "MATH172  HM", "MATH173  HM", "MATH174  HM", "MATH175  HM", "MATH176  HM", "MATH178  HM", "MATH188  HM", "MATH187  HM", "MATH184  HM", "MATH181  HM", "MATH179  HM", "MATH189  HM", *("MATH90%i__HM" for i in range(5)), *("CSCI90%i__HM" for i in range(5))),  # Hacked Credits 
        And("BioColloquium", "BIOL191  HM", "BIOL191  HM2"),
        "MATH198  HM",
        "MCBI199  HM",
        Or("ThesisOrClinic", And("CSClinic", "CSCI183  HM", "CSCI184  HM"), And("MathThesis", "MATH197  HM", "MATH197  HM2"), And("MathClinic", "MATH193  HM", "MATH193  HM2"), And("BioThesis", "BIOL193  HM", "BIOL193  HM2"), And("IntensiveBioThesis", "BIOL195  HM", "BIOL195  HM2"))
    ),
    "CS & Climate": And(
        "Maj_CSClimate",
        Or("Principles", "CSCI042  HM", "CSCI060  HM"),
        "CSCI070  HM",
        "MATH055  HM",
        Or("SysAlgs", "CSCI105  HM", "CSCI140  HM"),
        "CSCI123  HM",
        AtLeast("CSElective", 6, "MATH104  HM", "MATH106  HM", "MATH157  HM", "MATH164  HM", "MATH165  HM", "MATH167  HM", "MATH187  HM", "ENGR085A HM", "ENGR151  HM", "ENGR155  HM", "ENGR158  HM", "ENGR161  HM", "MCBI118A HM", "MCBI118B HM", "BIOL188  HM", "PHYS084  HM", "PHYS170  HM", "PSYC183  SC", "CHEM80  HM", "MCBI117  HM", "CSCI159  HM", "CSCI158  HM", "CSCI155  HM", "CSCI153  HM", "CSCI152  HM", "CSCI151  HM", "CSCI145  HM", "CSCI144  HM", "CSCI142  HM", "CSCI140  HM", "CSCI137  HM", "CSCI134  HM", "CSCI133  HM", "CSCI132  HM", "CSCI131  HM", "CSCI125  HM", "CSCI124  HM", "CSCI121  HM", "CSCI120  HM", "CSCI111  HM", "CSCI105  HM", *("CSCI90%i__HM" for i in range(5))), # Credit count hacked to consider either 140 or 105
        Or("Thermodynamics", "CHEM051  HM", "ENGR082  HM", "PHYS117  HM"),
        AtLeast("Areas", 6, Or("ProbStats", "BIOL154  HM", "MATH056  HM", "MATH062  HM", "PHYS117  HM"), "PHYS051  HM", "MATH082  HM", Or("Computational", "CHEM080  HM", "CSCI144  HM", "MATH164  HM", "PHYS064  HM")),
        "CLES101  HM",
        Or("ClimateImpacts", And("ClimateJustice", "CLES121  HM", "CLES122  HM"), "CLES130  HM", "CLES131  HM", "CHEM170  HM", "ENGR138  HM"),
        AtLeast("ClimateInterventions", 3, "CLES120  HM", And("ClimateJustice", "CLES121  HM", "CLES122  HM"), "CLES130  HM", "CHEM192  HM"),
        Or("ClimateContexts", "ECON146  HM", "ECON179G HM", "GEOG179I HM", "POST140  HM", "POST114  HM", "POST168  HM", "PSYC179O HM", "RLST179G HM", "SOSC188  HM", "SOC 179D HM"),
        Or("HumanCentered", "CSCI120  HM", "ENGR180  HM", "EA  185  PO"),
        And("CSColloquium", "CSCI195  HM", "CSCI195  HM2"),
        And("ClimateColloquium", "CLES199  HM", "CLES199  HM2"),
        "CSCI183  HM",
        "CSCI184  HM"
    ),
    "Core": And("Core",
        "BIOL023  HM",
        "BIOL046  HM",
        "CHEM024  HM",
        "CHEM042  HM",
        Or("IntroCS", "CSCI005  HM", "CSCI042  HM"),
        "CORE099  HM",
        "ENGR079  HM",
        "HSA 010  HM",
        "MATH019  HM",
        "MATH073  HM",
        "PHYS023  HM",
        Or("Mechanics", "PHYS024  HM", "PHYS024A HM"),
        "PHYS050  HM",
        "WRIT001  HM"
    ),
    "HSAs": And("HSAs",
        AtLeast("TenHSAs", 33, *(c.id for c in courses.values() if c.hsa)),
        AtLeast("MuddHums", 12, *(c.id for c in courses.values() if c.mudd_hum)),
        Or("WritingIntensive", *(c.id for c in courses.values() if c.writing))
    )
    }

    return majors


def compile_reqs(courses: Dict[str, Course]) -> List[ReqGroup]:
    course_reqs: List[ReqGroup] = []
    queue = [
        course.reqs for course in courses.values()
        if course.reqs is not None and course.reqs.num != 0
    ] + [reqs for reqs in get_majors_reqs(courses).values()]
    while queue:
        course_reqs.append(queue.pop())
        queue.extend(course_reqs[-1].groups)
    return course_reqs


if __name__ == "__main__":
    from sys import argv
    if len(argv) <= 3:
        print(f"Usage: {argv[0]} <out file> <files> ...")
    courses = parse_jsons(*(f for f in argv[2:] if f.endswith("json")))
    parse_files(courses, *(f for f in argv[2:] if not f.endswith("json")))
    course_reqs = compile_reqs(courses)
    write_reqs(argv[1], *course_reqs, courses=courses)
