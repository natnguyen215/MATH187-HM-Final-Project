from typing import Dict
from parsejson import Course, parse_jsons
from reqs import compile_reqs, parse_files


def make_tables(pname: str, lname: str, courses: Dict[str, Course]) -> None:
    with open(pname, "wt") as f:
        print("Writing portrait tables")
        f.write(r"\begin{longtable}{|l|l||l|l||l|l|}" + "\n    \\hline\n")
        f.write(r"    Course ID & Credits & Course ID & Credits & Course ID & Credits")
        col = 0
        for course in sorted(courses.values(), key=lambda c: c.id):
            if col == 0:
                f.write(r"\\\hline" + "\n    ")
            else:
                f.write(" & ")
            f.write(f"\\verb|{course.id}| & {course.credits}")
            col = (col + 1) % 3
        f.write(r"\\\hline" + "\n")
        f.write(r"    \caption{Credits by course.}" + "\n")
        f.write(r"    \label{tab:credits}" + "\n")
        f.write(r"\end{longtable}" + "\n")

        f.write(r"\begin{longtable}{|l|l||l|l||l|l|}" + "\n    \\hline\n")
        f.write(r"    Course ID & Offerings & Course ID & Offerings & Course ID & Offerings")
        col = 0
        for course in sorted(courses.values(), key=lambda c: c.id):
            if col == 0:
                f.write(r"\\\hline" + "\n    ")
            else:
                f.write(" & ")
            f.write(f"\\verb|{course.id}| & {', '.join(str(int(2 * o) + 1) for o in course.offerings)}")
            col = (col + 1) % 3
        f.write(r"\\\hline" + "\n")
        f.write(r"    \caption{Course offerings. Semesters are labeled sequentially, with semester 1 indicating the fall semester of a student's first year.}" + "\n")
        f.write(r"    \label{tab:offerings}" + "\n")
        f.write(r"\end{longtable}" + "\n")

        f.write(r"\begin{longtable}{|p{0.5\textwidth}|c|}" + "\n    \\hline\n")
        f.write(r"    Requirement Group Name & Required Groups\\\hline" + "\n")
        for req in sorted(compile_reqs(courses), key=lambda r: r.name):
            f.write(f"    \\verb|{req.name}| & {req.num}\\\\\\hline\n")
        f.write(r"    \caption{Number of requirements and credits needed to satisfy each requirement group.}" + "\n")
        f.write(r"    \label{tab:reqs-nums}" + "\n")
        f.write(r"\end{longtable}" + "\n")
    
    with open(lname, "wt") as f:
        print("Writing landscape tables")
        f.write(r"\begin{longtable}{|p{4.4in}|p{4.4in}|}" + "\n    \\hline\n")
        f.write(r"    Requirement Group Name & Required Groups\\\hline" + "\n")
        for req in sorted(compile_reqs(courses), key=lambda r: r.name):
            if not req.groups: continue
            f.write(f"    \\verb|{req.name}| & {', '.join([r'\verb|' + g.name + '|' for g in req.groups])}\\\\\\hline\n")
            # f.write(f"    \\verb|{req.name}| & {', '.join([r'\verb|' + g.name + '|' for g in req.groups])} & {', '.join([f'\\verb|{c}|' for c in req.pre])} & {', '.join([f'\\verb|{c}|' for c in req.co])}\\\\\\hline\n")
        f.write(r"    \caption{Requirement group contents: other requirement groups.}" + "\n")
        f.write(r"    \label{tab:reqs-groups}" + "\n")
        f.write(r"\end{longtable}" + "\n")

        f.write(r"\begin{longtable}{|p{4.4in}|p{4.4in}|}" + "\n    \\hline\n")
        f.write(r"    Requirement Group Name & Course Prequirequisites\\\hline" + "\n")
        for req in sorted(compile_reqs(courses), key=lambda r: r.name):
            if not req.pre: continue
            f.write(f"    \\verb|{req.name}| & {', '.join([f'\\verb|{c}|' for c in req.pre])}\\\\\\hline\n")
            # f.write(f"    \\verb|{req.name}| & {', '.join([r'\verb|' + g.name + '|' for g in req.groups])} & {', '.join([f'\\verb|{c}|' for c in req.pre])} & {', '.join([f'\\verb|{c}|' for c in req.co])}\\\\\\hline\n")
        f.write(r"    \caption{Requirement group contents: course prerequisites.}" + "\n")
        f.write(r"    \label{tab:reqs-prereqs}" + "\n")
        f.write(r"\end{longtable}" + "\n")

        f.write(r"\begin{longtable}{|p{4.4in}|p{4.4in}|}" + "\n    \\hline\n")
        f.write(r"    Requirement Group Name & Course Coquirequisites\\\hline" + "\n")
        for req in sorted(compile_reqs(courses), key=lambda r: r.name):
            if not req.co: continue
            f.write(f"    \\verb|{req.name}| & {', '.join([f'\\verb|{c}|' for c in req.co])}\\\\\\hline\n")
            # f.write(f"    \\verb|{req.name}| & {', '.join([r'\verb|' + g.name + '|' for g in req.groups])} & {', '.join([f'\\verb|{c}|' for c in req.pre])} & {', '.join([f'\\verb|{c}|' for c in req.co])}\\\\\\hline\n")
        f.write(r"    \caption{Requirement group contents: course prerequisites.}" + "\n")
        f.write(r"    \label{tab:reqs-coreqs}" + "\n")
        f.write(r"\end{longtable}" + "\n")


if __name__ == "__main__":
    from sys import argv
    if len(argv) <= 4:
        print(f"Usage: {argv[0]} <credits file> <reqs table> <files> ...")
    courses = parse_jsons(*(f for f in argv[3:] if f.endswith("json")))
    parse_files(courses, *(f for f in argv[3:] if not f.endswith("json")))
    make_tables(argv[1], argv[2], courses)