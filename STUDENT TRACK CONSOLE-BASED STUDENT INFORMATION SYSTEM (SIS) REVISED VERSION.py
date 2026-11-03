
import codecs
import os
import re
import sys
import textwrap
from datetime import date, datetime


SCHOOL_NAME = "PHINMA Education"
MIN_AGE = 17
MAX_AGE = 60
BACK = "8"
MAIN_MENU = "9"
INSTRUCTOR_USERNAME = "instructor"
INSTRUCTOR_PASSWORD = "1234"
DEFAULT_STUDENT_PASSWORD = "student123"
STUDENT_NAME_FIELDS = {"first_name", "middle_name", "last_name"}
YEAR_LEVELS = ("First Year", "Second Year", "Third Year", "Fourth Year")
OTHER_CHOICE = "Other (specify)"
GENDER_CHOICES = ("Male", "Female", "Non-binary", OTHER_CHOICE, "Prefer not to say")
NATIONALITY_CHOICES = ("Filipino", "American", "Chinese", "Japanese", "Korean", OTHER_CHOICE)
RELIGION_CHOICES = ("Roman Catholic", "Islam", "Iglesia ni Cristo", "Seventh Day Adventist", "Aglipay", OTHER_CHOICE)
PROFILE_CHOICES = {"gender": GENDER_CHOICES, "nationality": NATIONALITY_CHOICES, "religion": RELIGION_CHOICES}
SECTION_NUMBERS = ("01", "02", "03", "04", "05")
# Course codes and the year levels offered by this system.
COURSE_PROGRAMS = {
    "BSIT": {"name": "Bachelor of Science in Information Technology", "years": 4},
    "BSCS": {"name": "Bachelor of Science in Computer Science", "years": 4},
    "BSCpE": {"name": "Bachelor of Science in Computer Engineering", "years": 4},
    "BSBA": {"name": "Bachelor of Science in Business Administration", "years": 4},
    "BSA": {"name": "Bachelor of Science in Accountancy", "years": 4},
    "BSN": {"name": "Bachelor of Science in Nursing", "years": 4},
    "BSEd": {"name": "Bachelor of Secondary Education", "years": 4},
}


# ============================================
# VALIDATION FUNCTIONS
# ============================================

def valid_name(value):
    """Allow letters, spaces, apostrophes, periods, and hyphens; no digits."""
    return (
        1 <= len(value) <= 100
        and any(char.isalpha() for char in value)
        and all(char.isalpha() or char == " " or char in ".-'\u2019"
                for char in value)
    )


def valid_age(value):
    return (
        re.fullmatch(r"[0-9]{1,2}", value) is not None
        and MIN_AGE <= int(value) <= MAX_AGE
    )


def valid_contact(value):
    return re.fullmatch(r"09[0-9]{9}", value) is not None


def valid_email(value):
    if not 3 <= len(value) <= 254 or value.count("@") != 1:
        return False
    if any(char.isspace() for char in value):
        return False
    local, domain = value.split("@")
    if (not 1 <= len(local) <= 64 or local.startswith(".") or local.endswith(".")
            or ".." in local):
        return False
    if re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local) is None:
        return False
    labels = domain.split(".")
    return len(labels) >= 2 and all(
        re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
        is not None for label in labels
    )


def valid_student_id(value):
    return re.fullmatch(r"[0-9]{2}-[0-9]{4}-[0-9]{6}", value) is not None


def age_on(birthday, today=None):
    today = today or date.today()
    return today.year - birthday.year - (
        (today.month, today.day) < (birthday.month, birthday.day)
    )


def valid_dob(value):
    """Require a real MM/DD/YYYY date and an age between 17 and 60."""
    if re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", value) is None:
        return False
    try:
        birthday = datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        return False
    return MIN_AGE <= age_on(birthday) <= MAX_AGE


def valid_words(value):
    """Text-only fields may contain letters, spaces, and common punctuation."""
    return (
        1 <= len(value) <= 150
        and any(char.isalpha() for char in value)
        and all(char.isalpha() or char == " " or char in "/.,&()-'\u2019"
                for char in value)
    )


def valid_gender(value):
    return valid_words(value)


def valid_course(value):
    return value in COURSE_PROGRAMS


def course_year_levels(course):
    duration = COURSE_PROGRAMS.get(course, {}).get("years", 0)
    return YEAR_LEVELS[:duration]


def valid_year_level(value):
    return value in YEAR_LEVELS


def normalize_student_name(value):
    return " ".join(value.split()).upper()


def valid_section(value):
    """Require FB + year number, a known course code, and section 01-05."""
    match = re.fullmatch(r"FB([1-4])-([A-Z]+)-([0-9]{2})", value)
    if not match:
        return False
    year, course_code, number = match.groups()
    courses = {code.upper(): code for code in COURSE_PROGRAMS}
    return (
        course_code in courses and number in SECTION_NUMBERS
        and int(year) <= COURSE_PROGRAMS[courses[course_code]]["years"]
    )


def make_section_code(course, year_level, section_number):
    if (not valid_course(course) or year_level not in course_year_levels(course)
            or section_number not in SECTION_NUMBERS):
        return ""
    year_number = YEAR_LEVELS.index(year_level) + 1
    return f"FB{year_number}-{course.upper()}-{section_number}"


def synchronize_section(draft):
    """Keep the chosen section number when course or year changes."""
    previous = draft["section"]
    number = previous.rsplit("-", 1)[-1] if valid_section(previous) else ""
    draft["section"] = make_section_code(draft["course"], draft["year_level"], number)


def valid_description(value):
    """Addresses need letters and may include numbers and common punctuation."""
    return (
        1 <= len(value) <= 500
        and any(char.isalpha() for char in value)
        and all(char.isalpha() or char in "0123456789 .,'\u2019-/()&:+%#;"
                for char in value)
    )


def valid_username(value):
    return re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,29}", value) is not None


def valid_password(value):
    return 1 <= len(value) <= 128 and value.isprintable() and not any(
        char.isspace() for char in value
    )


def valid_registration_password(value):
    return (
        valid_password(value) and len(value) >= 8
        and any(char.isalpha() for char in value)
        and any(char in "0123456789" for char in value)
    )


def field(key, label, validator, error, optional=False):
    return {"key": key, "label": label, "validator": validator,
            "error": error, "optional": optional}


NAME_ERROR = "Use letters, spaces, apostrophes, periods, or hyphens; no digits."
CONTACT_ERROR = "Use exactly 11 digits starting with 09 (example: 09123456789)."
EMAIL_ERROR = "Enter a valid email with @ and a domain dot (example: name@gmail.com)."
TEXT_ERROR = "Use letters, spaces, and common punctuation only; no numbers."
DESCRIPTION_ERROR = "Enter a description with letters; numbers and common punctuation are allowed."

# The same field definitions drive Add, Edit, validation, and the full view.
PROFILE_SECTIONS = [
    ("Student Details", [
        field("first_name", "First Name", valid_name, NAME_ERROR),
        field("middle_name", "Middle Name", valid_name, NAME_ERROR, optional=True),
        field("last_name", "Last Name", valid_name, NAME_ERROR),
        field("age", "Age (17-60)", valid_age, "Enter digits only, from 17 to 60."),
        field("date_of_birth", "Date of Birth (MM/DD/YYYY)", valid_dob,
              "Use a real MM/DD/YYYY birth date for someone aged 17 to 60."),
        field("gender", "Gender / Sex", valid_gender,
              "Choose a gender option or use Other to specify a value without digits."),
        field("email", "Email Address", valid_email, EMAIL_ERROR),
        field("contact", "Phone Number", valid_contact, CONTACT_ERROR),
        field("address", "Home Address", valid_description, DESCRIPTION_ERROR),
        field("religion", "Religion", valid_words, TEXT_ERROR, optional=True),
        field("nationality", "Nationality", valid_words, "Enter a nationality without digits."),
    ]),
    ("Academic Background", [
        field("course", "Course / Program", valid_course, "Choose a listed course abbreviation."),
        field("year_level", "Year Level", valid_year_level,
              "Choose a listed year level from First Year to Fourth Year."),
        field("section", "Section", valid_section,
              "Choose a section code matching your course and year (example: FB1-BSIT-03)."),
        field("previous_school", "Previous School Attended", valid_words, TEXT_ERROR),
    ]),
    ("Guardian & Parent Information", [
        field("mother_name", "Mother's Full Name", valid_name, NAME_ERROR, optional=True),
        field("father_name", "Father's Full Name", valid_name, NAME_ERROR, optional=True),
        field("guardian_name", "Guardian's Full Name", valid_name, NAME_ERROR, optional=True),
        field("guardian_relationship", "Contact's Relationship to Student", valid_words,
              "Enter a relationship such as Mother, Father, Aunt, or Guardian."),
        field("guardian_contact", "Parent / Guardian Phone Number", valid_contact, CONTACT_ERROR),
        field("guardian_email", "Parent / Guardian Email", valid_email, EMAIL_ERROR, optional=True),
    ]),
]


def make_student(password, first_name="", middle_name="", last_name=""):
    student = {item["key"]: "" for _, fields in PROFILE_SECTIONS for item in fields}
    first_name, middle_name, last_name = (
        normalize_student_name(value) for value in (first_name, middle_name, last_name)
    )
    name = " ".join(part for part in (first_name, middle_name, last_name) if part and part != "N/A")
    student.update(
        password=password, first_name=first_name, middle_name=middle_name,
        last_name=last_name, name=name, school=SCHOOL_NAME, profile_completed=False,
    )
    return student


students = {
    "02-2627-010087": make_student(DEFAULT_STUDENT_PASSWORD, "ALEXANDER JOHN", "B.", "ABROGAR"),
    "02-2627-010245": make_student(DEFAULT_STUDENT_PASSWORD, "TRISHA KIM", "L.", "BUNTAG"),
    "02-2627-009352": make_student(DEFAULT_STUDENT_PASSWORD, "JOHN VINCENT", "P.", "CABATINGAN"),
    "02-2627-010334": make_student(DEFAULT_STUDENT_PASSWORD, "JOHNMART", "B.", "CERO"),
    "02-2627-010543": make_student(DEFAULT_STUDENT_PASSWORD, "JESSIE", "V.", "RERORA"),
    "02-2627-010080": make_student(DEFAULT_STUDENT_PASSWORD, "RHEANMART", "P.", "YAP"),
}


# ============================================
# SHARED NAVIGATION AND DISPLAY
# ============================================

class BackRequested(Exception):
    """Return to the caller, or move to the previous form field."""


class MainMenuRequested(Exception):
    """Unwind any open screen and log out to the main menu."""


def arrow_keys_available():
    """IDE input boxes and redirected input retain ordinary numbered input."""
    try:
        return os.name in {"nt", "posix"} and sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, OSError):
        return False


def character_key(character):
    if character == "\x03":
        raise KeyboardInterrupt
    if character in {"", "\x04", "\x1a"}:
        return "eof", ""
    if character in {"\r", "\n"}:
        return "enter", ""
    if character in {"\b", "\x7f"}:
        return "backspace", ""
    if character.isprintable():
        return "text", character
    return "other", ""


def windows_key():
    import msvcrt

    character = msvcrt.getwch()
    if character in {"\x00", "\xe0"}:
        code = msvcrt.getwch()
        return {"K": "left", "P": "down"}.get(code, "other"), ""
    return character_key(character)


def posix_key(fd, decoder):
    import select

    raw = os.read(fd, 1)
    if not raw:
        return "eof", ""
    if raw == b"\x1b":
        # Normal and application-mode arrow sequences: ESC [ D / ESC O D.
        sequence = b""
        while len(sequence) < 32 and select.select([fd], [], [], 0.05)[0]:
            part = os.read(fd, 1)
            if not part:
                break
            sequence += part
            if len(sequence) == 1 and part not in {b"[", b"O"}:
                break
            if len(sequence) >= 2 and b"@" <= part <= b"~":
                break
        return {b"[D": "left", b"OD": "left", b"[B": "down", b"OB": "down"}.get(
            sequence, "other"
        ), ""
    character = decoder.decode(raw)
    while not character:
        raw = os.read(fd, 1)
        if not raw:
            return "eof", ""
        character = decoder.decode(raw)
    return character_key(character)


def keyboard_line(prompt, next_key):
    """Read one line while handling immediate navigation keys."""
    print(prompt, end="", flush=True)
    characters = []
    down_count = 0
    while True:
        key, character = next_key()
        if key == "left":
            print()
            raise BackRequested
        if key == "down":
            down_count += 1
            if down_count == 2:
                print()
                raise MainMenuRequested
            continue
        # Any other key resets the count, so the Down presses must be consecutive.
        down_count = 0
        if key == "enter":
            print()
            return "".join(characters)
        if key == "eof":
            print()
            if characters:
                return "".join(characters)
            raise EOFError
        if key == "backspace" and characters:
            characters.pop()
            print("\b \b", end="", flush=True)
        elif key == "text":
            characters.append(character)
            print(character, end="", flush=True)


def console_input(prompt):
    if not arrow_keys_available():
        return input(prompt)
    if os.name == "nt":
        return keyboard_line(prompt, windows_key)

    import termios
    import tty

    fd = sys.stdin.fileno()
    previous_settings = termios.tcgetattr(fd)
    decoder = codecs.getincrementaldecoder(sys.stdin.encoding or "utf-8")("replace")
    try:
        tty.setcbreak(fd, when=termios.TCSANOW)
        return keyboard_line(prompt, lambda: posix_key(fd, decoder))
    finally:
        # Restore echo and line editing even after navigation or interruption.
        termios.tcsetattr(fd, termios.TCSADRAIN, previous_settings)


def heading(title, space_after=True):
    print("\n" + "=" * 68)
    print(title.center(68))
    print("=" * 68)
    if space_after:
        print()


def read_input(prompt, back_label="Previous screen", main_label="Main Menu (log out)",
               guide=None, value_validator=None):
    if arrow_keys_available():
        print(f"Left Arrow: {back_label} | Down Arrow twice: {main_label}")
    else:
        print(f"{BACK}. {back_label} | {MAIN_MENU}. {main_label}")
    if guide:
        print(guide)
    value = console_input(prompt).strip()
    if value in {BACK, MAIN_MENU} and value_validator and value_validator(value):
        # A grade or section can legitimately be 8 or 9. Keep both uses available.
        while True:
            print(f"\n1. Use '{value}' as the field value")
            choice = read_input("Enter your choice: ", back_label, main_label)
            if choice == "1":
                return value
            print(f"Invalid choice. Enter 1, {BACK}, or {MAIN_MENU}.")
    if value == BACK:
        raise BackRequested
    if value == MAIN_MENU:
        raise MainMenuRequested
    return value


def display_value(label, value, width=84):
    prefix = f"{label}: "
    lines = textwrap.wrap(
        str(value or "Not provided"), width=width,
        initial_indent=prefix, subsequent_indent=" " * min(len(prefix), 8),
    )
    print("\n".join(lines))


def full_name(student):
    parts = [student.get(key, "") for key in ("first_name", "middle_name", "last_name")]
    return normalize_student_name(
        " ".join(value for value in parts if value and value != "N/A") or student.get("name", "")
    )


def roster_name(student):
    given = " ".join(
        student[key] for key in ("first_name", "middle_name")
        if student.get(key) and student[key] != "N/A"
    )
    last = student.get("last_name", "")
    if last and given:
        return normalize_student_name(f"{last}, {given}")
    return full_name(student) or "Not provided"


def display_student(student_id, student=None, full=False):
    student = students[student_id] if student is None else student
    if full:
        for title, fields in PROFILE_SECTIONS:
            heading(title.upper(), space_after=False)
            for item in fields:
                display_value(item["label"], student[item["key"]], width=68)
        print("=" * 68)
        return

    heading("INITIAL STUDENT DETAILS")
    display_value("Student ID", student_id)
    display_value("Full Name", full_name(student))
    display_value("School", student["school"])
    display_value("Profile Status", "Completed" if student["profile_completed"] else "Not yet submitted")
    for label, key in [
        ("Age", "age"), ("Gender / Sex", "gender"),
        ("Course / Program", "course"), ("Year Level", "year_level"),
        ("Section", "section"), ("Phone Number", "contact"), ("Email Address", "email"),
    ]:
        display_value(label, student[key])
    print("=" * 68)


def view_record(student_id, full=False, back_label="Previous screen"):
    while True:
        display_student(student_id, full=full)
        print("1. View " + ("Initial Details" if full else "Full Details"))
        try:
            choice = read_input("Enter your choice: ", back_label)
        except BackRequested:
            return
        if choice == "1":
            full = not full
        else:
            print(f"Invalid choice. Enter 1, {BACK}, or {MAIN_MENU}.")


# ============================================
# STUDENT LOGIN AND MENU
# ============================================

def student_login():
    step = 0
    student_id = ""
    while True:
        heading("STUDENT LOGIN")
        try:
            if step == 0:
                student_id = read_input(
                    "Student ID: ", "Back to Main Menu", "Main Menu",
                    guide="Format: 02-2627-010087",
                )
                if not valid_student_id(student_id):
                    print("Invalid Student ID. Use the format 02-2627-010087.")
                elif student_id not in students:
                    print("Student ID not found.")
                else:
                    step = 1
            else:
                print(f"Student ID: {student_id}")
                password = read_input("Password: ", "Back to Student ID", "Main Menu")
                if not valid_password(password):
                    print("Enter a non-empty password up to 128 characters, without spaces.")
                    continue
                if password != students[student_id]["password"]:
                    print("Incorrect password. Please try again.")
                    continue
                if not full_name(students[student_id]):
                    if not setup_student_name(student_id):
                        continue
                print(f"\nLogin successful! Welcome, {full_name(students[student_id])}!")
                student_menu(student_id)
                return
        except BackRequested:
            if step == 0:
                return
            step = 0


def student_menu(student_id):
    while True:
        heading("STUDENT MENU")
        print(f"Student: {full_name(students[student_id])}")
        print("1. Add Information")
        print("2. Edit Information")
        print("3. View Information")
        print("4. Logout to Main Menu")
        try:
            choice = read_input("Enter your choice: ", "Back to Main Menu (log out)")
        except BackRequested:
            return
        if choice == "1":
            add_information(student_id)
        elif choice == "2":
            edit_information(student_id)
        elif choice == "3":
            view_my_information(student_id)
        elif choice == "4":
            print("You have been logged out.")
            return
        else:
            print(f"Invalid choice. Enter 1-4, {BACK}, or {MAIN_MENU}.")


# ============================================
# STUDENT REGISTRATION
# ============================================

def register_student():
    password_error = "Use 8-128 characters with at least one letter and one digit; no spaces."
    fields = [
        field("student_id", "Student ID", valid_student_id, "Use the format 02-2627-010087."),
        *PROFILE_SECTIONS[0][1][:3],
        field("password", "Create Password", valid_registration_password, password_error),
        field("confirm_password", "Confirm Password", valid_registration_password, password_error),
    ]
    draft = {item["key"]: "" for item in fields}
    index = 0
    while True:
        if index == len(fields):
            heading("REVIEW STUDENT REGISTRATION")
            display_value("Student ID", draft["student_id"])
            display_value("Full Name", roster_name(draft))
            print("1. Confirm and Register Account")
            try:
                choice = read_input("Enter your choice: ", "Back to Confirm Password", "Main Menu")
            except BackRequested:
                index -= 1
                continue
            if choice != "1":
                print(f"Invalid choice. Enter 1, {BACK}, or {MAIN_MENU}.")
                continue
            student_id = draft["student_id"]
            if student_id in students:
                print("This Student ID is already registered. Please use a different ID.")
                index = 0
                continue
            students[student_id] = make_student(
                draft["password"], draft["first_name"], draft["middle_name"], draft["last_name"],
            )
            print("\nAccount successfully registered!")
            print("You can now log in and complete your information.")
            print("Your account is now visible in the instructor's student list.")
            return

        item = fields[index]
        key = item["key"]
        heading(f"STUDENT REGISTRATION - {index + 1}/{len(fields)}")
        if draft[key]:
            if "password" not in key:
                display_value("Current value", draft[key])
            print("Press ENTER to keep the current value.")
        if item["optional"]:
            print("Middle name is optional: press ENTER or type N/A if none.")
        if key == "password":
            print(password_error)
        try:
            value = read_input(
                item["label"] + ": ",
                "Previous field" if index else "Back to Main Menu", "Main Menu",
                guide="Format: 02-2627-010087" if key == "student_id" else None,
            )
        except BackRequested:
            if index == 0:
                return
            index -= 1
            continue
        if not value:
            value = draft[key] or ("N/A" if item["optional"] else "")
        elif item["optional"] and value.upper() in {"N/A", "NA"}:
            value = "N/A"
        if not field_is_valid(item, value):
            print(item["error"])
            continue
        if key == "student_id" and value in students:
            print("This Student ID is already registered. Please use a different ID.")
            continue
        if key == "confirm_password" and value != draft["password"]:
            print("Passwords do not match. Please confirm the same password.")
            continue
        if key in STUDENT_NAME_FIELDS:
            value = normalize_student_name(value)
        draft[key] = value
        index += 1


# ============================================
# ADD / EDIT INFORMATION
# ============================================

def field_is_valid(item, value):
    return bool(value) and (
        (item["optional"] and value == "N/A") or item["validator"](value)
    )


def section_is_complete(fields, draft):
    return all(field_is_valid(item, draft[item["key"]]) for item in fields)


def read_other_choice(label, current=""):
    while True:
        heading(f"SPECIFY {label.upper()}")
        if current:
            display_value("Current value", current)
            print("Press ENTER to keep the current value.")
        value = read_input(f"Specify {label}: ", f"Back to {label} Choices")
        if not value:
            value = current
        if valid_words(value) and value.casefold() not in {"other", OTHER_CHOICE.casefold()}:
            return " ".join(value.split())
        print("Please specify a value using letters and common punctuation; no numbers.")


def collect_section(draft, title, fields,
                    first_back_label="Back to Information Sections", announce_completion=True):
    """Back moves one field at a time; drafts survive returning to sections."""
    index = 0
    while index < len(fields):
        item = fields[index]
        key = item["key"]
        heading(f"{title.upper()} - {index + 1}/{len(fields)}")
        if draft[key]:
            display_value("Current value", draft[key])
            print("Press ENTER to keep the current value.")
        if item["optional"]:
            print("Optional: type N/A if none or unavailable; ENTER skips an empty field.")
        options = {}
        if key in PROFILE_CHOICES:
            choices = PROFILE_CHOICES[key]
            options = {str(number): value for number, value in enumerate(choices, 1)}
            for number, value in options.items():
                print(f"{number}. {value}")
        elif key == "course":
            options = {str(number): code for number, code in enumerate(COURSE_PROGRAMS, 1)}
            for number, code in options.items():
                print(f"{number}. {code} - {COURSE_PROGRAMS[code]['name']}")
        elif key == "year_level":
            if not valid_course(draft["course"]):
                print("Choose a course before selecting your year level.")
                course_index = next((i for i, entry in enumerate(fields) if entry["key"] == "course"), None)
                if course_index is None:
                    return False
                index = course_index
                continue
            print(f"Course: {draft['course']}")
            options = {str(number): year for number, year in enumerate(course_year_levels(draft["course"]), 1)}
            for number, year in options.items():
                print(f"{number}. {year}")
        elif key == "section":
            missing = "course" if not valid_course(draft["course"]) else "year_level"
            if draft["year_level"] not in course_year_levels(draft["course"]):
                print("Choose your course and year before selecting a section.")
                previous_index = next((i for i, entry in enumerate(fields) if entry["key"] == missing), None)
                if previous_index is None:
                    return False
                index = previous_index
                continue
            print(f"Course: {draft['course']} | Year: {draft['year_level']}")
            options = {
                str(number): make_section_code(draft["course"], draft["year_level"], section)
                for number, section in enumerate(SECTION_NUMBERS, 1)
            }
            for number, code in options.items():
                print(f"{number}. {code}")
        try:
            value = read_input(
                "Choose a number: " if options else item["label"] + ": ",
                "Previous field" if index else first_back_label,
                value_validator=(lambda entered: entered in options) if options else item["validator"],
            )
        except BackRequested:
            if index == 0:
                return False
            index -= 1
            continue
        if not value:
            value = draft[key] or ("N/A" if item["optional"] else "")
        elif item["optional"] and value.upper() in {"N/A", "NA"}:
            value = "N/A"
        elif options:
            if value not in options:
                print("Choose a listed number.")
                continue
            value = options[value]
            if value == OTHER_CHOICE:
                current = draft[key] if draft[key] not in options.values() else ""
                try:
                    value = read_other_choice(item["label"], current)
                except BackRequested:
                    continue
        if not field_is_valid(item, value):
            print(item["error"])
            continue
        if key in STUDENT_NAME_FIELDS:
            value = normalize_student_name(value)
        if key == "course" and draft["year_level"] not in course_year_levels(value):
            draft["year_level"] = ""
        draft[key] = value
        if key in {"course", "year_level"}:
            synchronize_section(draft)
        index += 1
    if announce_completion:
        print(f"\n{title} completed. Choose another section or Review and Save.")
    return True


def setup_student_name(student_id):
    """Collect a missing name after authentication, before the welcome message."""
    print("\nPlease enter your name to complete your first login.")
    draft = dict(students[student_id])
    name_fields = PROFILE_SECTIONS[0][1][:3]
    if not collect_section(
        draft, "Student Name", name_fields,
        first_back_label="Back to Password", announce_completion=False,
    ):
        return False
    student = students[student_id]
    for item in name_fields:
        student[item["key"]] = draft[item["key"]]
    student["name"] = full_name(student)
    return True


def profile_errors(draft):
    errors = []
    for title, fields in PROFILE_SECTIONS:
        for item in fields:
            if not field_is_valid(item, draft[item["key"]]):
                errors.append(f"{title} - {item['label']}: {item['error']}")
    if valid_course(draft["course"]) and draft["year_level"] not in course_year_levels(draft["course"]):
        errors.append("Academic Background - Select a valid year level for your chosen course.")
    if valid_section(draft["section"]):
        number = draft["section"].rsplit("-", 1)[1]
        if draft["section"] != make_section_code(draft["course"], draft["year_level"], number):
            errors.append("Academic Background - Section must match the selected course and year level.")
    if valid_age(draft["age"]) and valid_dob(draft["date_of_birth"]):
        birthday = datetime.strptime(draft["date_of_birth"], "%m/%d/%Y").date()
        actual_age = age_on(birthday)
        if int(draft["age"]) != actual_age:
            errors.append(
                f"Student Details - Age must match Date of Birth. "
                f"That birth date gives age {actual_age} today."
            )
    if not any(
        valid_name(draft[key])
        for key in ("mother_name", "father_name", "guardian_name")
    ):
        errors.append("Guardian & Parent Information - Provide at least one parent's or guardian's name.")
    return errors


def review_and_save(student_id, draft):
    errors = profile_errors(draft)
    if errors:
        print("\nPlease complete or correct the following before saving:")
        for error in errors:
            print("- " + error)
        return False
    preview = dict(draft)
    preview["name"] = full_name(draft)
    preview["profile_completed"] = True
    while True:
        display_student(student_id, preview, full=True)
        print("DRAFT PREVIEW - changes have not been saved yet.")
        print("1. Confirm and Save Information")
        try:
            choice = read_input("Enter your choice: ", "Back to Information Sections")
        except BackRequested:
            return False
        if choice == "1":
            students[student_id].update(preview)
            print("\nStudent information successfully saved!")
            return True
        print(f"Invalid choice. Enter 1, {BACK}, or {MAIN_MENU}.")


def information_form(student_id, editing=False):
    draft = dict(students[student_id])
    title = "EDIT INFORMATION" if editing else "ADD INFORMATION"
    section_count = len(PROFILE_SECTIONS)
    save_choice = str(section_count + 1)
    print(f"\nComplete all {section_count} sections, then choose Review and Save.")
    print("Changes stay in this draft until you confirm saving.")
    print("Leaving this form for the Student Menu or Main Menu discards the draft.")
    try:
        while True:
            heading(title)
            for number, (section_title, fields) in enumerate(PROFILE_SECTIONS, 1):
                status = "Complete" if section_is_complete(fields, draft) else "Incomplete"
                print(f"{number}. {section_title} [{status}]")
            print(f"{save_choice}. Review and Save Information")
            try:
                choice = read_input("Choose a section: ", "Back to Student Menu (discard draft)")
            except BackRequested:
                print("Returned to Student Menu. Unsaved draft discarded.")
                return
            if choice in {str(number) for number in range(1, section_count + 1)}:
                section_title, fields = PROFILE_SECTIONS[int(choice) - 1]
                collect_section(draft, section_title, fields)
            elif choice == save_choice:
                if review_and_save(student_id, draft):
                    return
            else:
                print(f"Invalid choice. Enter 1-{save_choice}, {BACK}, or {MAIN_MENU}.")
    except MainMenuRequested:
        print("Unsaved draft discarded.")
        raise


def add_information(student_id):
    if students[student_id]["profile_completed"]:
        print("An existing profile was found. Its current information is loaded below.")
    information_form(student_id)


def edit_information(student_id):
    information_form(student_id, editing=True)


def view_my_information(student_id):
    view_record(student_id, full=True, back_label="Back to Student Menu")


# ============================================
# INSTRUCTOR LOGIN, MENU, AND STUDENT VIEWS
# ============================================

def instructor_login():
    step = 0
    username = ""
    while True:
        heading("INSTRUCTOR LOGIN")
        try:
            if step == 0:
                username = read_input("Username: ", "Back to Main Menu", "Main Menu")
                if not valid_username(username):
                    print("Use 3-30 characters: start with a letter, then letters, digits, _, ., or -.")
                    continue
                step = 1
            else:
                print(f"Username: {username}")
                password = read_input("Password: ", "Back to Username", "Main Menu")
                if not valid_password(password):
                    print("Enter a non-empty password up to 128 characters, without spaces.")
                    continue
                if username == INSTRUCTOR_USERNAME and password == INSTRUCTOR_PASSWORD:
                    print("\nInstructor login successful!")
                    instructor_menu()
                    return
                print("Invalid username or password. Please try again.")
                step = 0
        except BackRequested:
            if step == 0:
                return
            step = 0


def instructor_menu():
    while True:
        heading("INSTRUCTOR MENU")
        print("1. View Student Information")
        print("2. Logout to Main Menu")
        try:
            choice = read_input("Enter your choice: ", "Back to Main Menu (log out)")
        except BackRequested:
            return
        if choice == "1":
            view_student_information()
        elif choice == "2":
            print("Instructor logged out.")
            return
        else:
            print(f"Invalid choice. Enter 1, 2, {BACK}, or {MAIN_MENU}.")


def display_student_list():
    heading("STUDENT LIST - INITIAL DETAILS")
    print("Select a student to see their complete, unshortened information.\n")
    header = (
        f"{'No.':<4} | {'Student ID':^16} | {'Full Name':^32} | "
        f"{'Course':^16} | {'Year Level':^15} | {'Section':^12}"
    )
    print("=" * len(header))
    print(header)
    print("=" * len(header))
    for number, (student_id, student) in enumerate(students.items(), 1):
        name = roster_name(student)
        course = student["course"] or "Not provided"
        year = student["year_level"] or "Not provided"
        section = student["section"] or "Not provided"
        print(
            f"{number:<4} | {student_id:<16} | {name[:32]:<32} | "
            f"{course[:16]:<16} | {year[:15]:<15} | {section[:12]:<12}"
        )


def view_student_information():
    while True:
        display_student_list()
        student_ids = list(students)
        numbered_students = {str(number): student_id for number, student_id in enumerate(student_ids, 1)}
        try:
            choice = read_input(
                "Enter the student's list number or full Student ID: ", "Back to Instructor Menu",
                value_validator=lambda value: value in numbered_students,
            )
        except BackRequested:
            return
        if choice in students:
            student_id = choice
        elif choice in numbered_students:
            student_id = numbered_students[choice]
        else:
            print("Student not found. Choose a listed number or a complete formatted Student ID.")
            continue
        view_record(student_id, back_label="Back to Student List")


# ============================================
# MAIN MENU
# ============================================

def main():
    while True:
        heading("STUDENT INFORMATION SYSTEM")
        print("1. Student Login")
        print("2. Instructor Login")
        print("3. Register Student Account")
        print("4. Exit")
        try:
            choice = console_input("Enter your choice: ").strip()
            if choice == "1":
                student_login()
            elif choice == "2":
                instructor_login()
            elif choice == "3":
                register_student()
            elif choice == "4":
                print("\nThank you for using the Student Information System. Goodbye!")
                return
            else:
                print("Invalid choice. Enter 1, 2, 3, or 4.")
        except BackRequested:
            continue
        except MainMenuRequested:
            print("\nReturned to Main Menu. You are logged out.")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nProgram closed.")
