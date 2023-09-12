import os
import shutil
from typing import Dict, List
import drawsvg as draw
from svglib.svglib import svg2rlg, register_font
from reportlab.graphics import renderPDF

from tqdm import tqdm

from utils import HolidayType, Subject, SubjectProps, SubjectType, Week


# Month number to month name
_MONTH_NAME = [
    "gen",
    "febr",
    "març",
    "abr",
    "maig",
    "juny",
    "jul",
    "ago",
    "set",
    "oct",
    "nov",
    "des",
]


def render_to_pdf(
    weeks: List[Week],
    subjects_props: Dict[str, SubjectProps],
    start_hour: int = 9,
    end_hour: int = 20,
):
    register_font("calibri", "calibri_bold.ttf", "bold")

    n_hours = end_hour - start_hour

    width = 1000.0
    height = 500.0

    day_label_height = height / (n_hours + 1)

    work_height = height - day_label_height
    day_height = work_height / n_hours

    text_size = day_height * 0.3
    hour_label_width = width * 0.0031 * text_size
    work_width = width - hour_label_width
    day_width = work_width / 5

    text_correction = -text_size * 0.2

    light_line_width = height / 1000
    dark_line_width = 2 * light_line_width

    def get_day_x(day):
        return hour_label_width + day_width * day

    def get_hour_y(hour):
        # return height - day_label_height - day_height - (hour - start_hour) * day_height
        return (hour - start_hour) * day_height + day_label_height

    # Create path to save the files
    if os.path.exists("results"):
        shutil.rmtree("results")
    os.mkdir("results")

    if os.path.exists("temp"):
        shutil.rmtree("temp")
    os.mkdir("temp")

    for week_n, week in enumerate(tqdm(weeks)):
        d = draw.Drawing(width, height)

        d.append(
            draw.Rectangle(
                0,
                0,
                width,
                height,
                fill="white",
                stroke="black",
                stroke_width=dark_line_width,
            )
        )  # Background

        # For each day get the subjects (data)
        for day_n, day in week.days.items():
            day_x = get_day_x(day_n)

            # Draw gray background on the day label
            if day.holiday is not None:
                d.append(
                    draw.Rectangle(
                        day_x,
                        0,
                        day_width,
                        day_height,
                        fill="#BEBEBE",
                        stroke="black",
                        stroke_width="0.2",
                    )
                )

            for hour, subjects in day.hours.items():
                y = get_hour_y(hour)

                s: Subject
                for i, s in enumerate(subjects):
                    new_width = day_width / len(subjects)

                    x = day_x + i * new_width

                    props = subjects_props[s.id]

                    text = props.name
                    if s.type == SubjectType.SEMINAR:
                        text += f"\nSe{s.group}"
                    elif s.type == SubjectType.PROBLEMS:
                        text += f"\nPb{s.group}"
                    elif s.type == SubjectType.LABORATORY:
                        text += f"\nPr{s.group}"
                    elif s.type == SubjectType.EXAM:
                        text += f"\n{s.group} Examen"
                    elif s.type == SubjectType.UNKNOWN:
                        text += f"\n{s.group} (??)"
                    # if s.type == SubjectType.SEMINAR:
                    #     text += f" Se{s.group}"
                    # elif s.type == SubjectType.PROBLEMS:
                    #     text += f" Pb{s.group}"
                    # elif s.type == SubjectType.LABORATORY:
                    #     text += f" Pr{s.group}"
                    # elif s.type == SubjectType.EXAM:
                    #     text += f" {s.group} Examen"
                    # elif s.type == SubjectType.UNKNOWN:
                    #     text += f" {s.group} (??)"

                    text += f"\n{s.classroom}"

                    d.append(
                        draw.Rectangle(
                            x,
                            y,
                            new_width,
                            day_height,
                            fill=props.color,
                            stroke="black",
                            stroke_width=dark_line_width,
                        )
                    )

                    d.append(
                        draw.Text(
                            text,
                            text_size,
                            x + new_width / 2,
                            y + day_height / 2 + text_correction,
                            center=True,
                            fill="black",
                            font_weight="bold",
                            font_family="calibri",
                        )
                    )

        # Draw grid
        for i in range(1, 5):
            x = hour_label_width + (day_width * i)
            d.append(
                draw.Line(
                    x, 0, x, height, stroke="black", stroke_width=light_line_width
                )
            )

        for i in range(n_hours - 1):
            y = day_height * (i + 1) + day_label_height
            d.append(
                draw.Line(0, y, width, y, stroke="black", stroke_width=light_line_width)
            )

        d.append(
            draw.Line(
                0,
                day_label_height,
                width,
                day_label_height,
                stroke="black",
                stroke_width=dark_line_width,
            )
        )
        d.append(
            draw.Line(
                hour_label_width,
                0,
                hour_label_width,
                height,
                stroke="black",
                stroke_width=dark_line_width,
            )
        )

        # Draw day and month text on top
        for day_n, day in week.days.items():
            day_x = get_day_x(day_n)
            d.append(
                draw.Text(
                    f"{day.date.day}-{_MONTH_NAME[day.date.month-1]}",
                    text_size,
                    day_x + day_width / 2,
                    day_label_height / 2 + text_correction,
                    center=True,
                    fill="black",
                    font_weight="bold",
                    font_family="calibri",
                )
            )

        # Draw hours (only one time)
        for hour in range(start_hour, end_hour):
            day_y = get_hour_y(hour)
            d.append(
                draw.Text(
                    # f"{hour}-{hour+1}",
                    f"{hour}:00",
                    text_size,
                    hour_label_width / 2,
                    day_y + day_height / 2 + text_correction,
                    center=True,
                    fill="black",
                    font_weight="bold",
                    font_family="calibri",
                )
            )

        # Draw holidays as gray
        for day_n, day in week.days.items():
            if day.holiday is not None:
                day_x = get_day_x(day_n)
                d.append(
                    draw.Rectangle(
                        day_x,
                        day_label_height,
                        day_width,
                        work_height,
                        fill="#BEBEBE",
                        stroke="black",
                        stroke_width="0.2",
                    )
                )

                holiday_text = None
                if day.holiday == HolidayType.FESTIU:
                    holiday_text = "FESTIU"
                elif day.holiday == HolidayType.NO_LECTIU:
                    holiday_text = "NO LECTIU"
                else:
                    holiday_text = "FESTA??"

                d.append(
                    draw.Text(
                        holiday_text,
                        text_size,
                        day_x + day_width / 2,
                        work_height / 2 + day_label_height + text_correction,
                        center=True,
                        fill="black",
                        font_weight="bold",
                        font_family="calibri",
                    )
                )

        with open(f"temp/{week_n}.svg", "w", encoding="utf8") as file:
            d.as_svg(output_file=file)

        drawing = svg2rlg(f"temp/{week_n}.svg")
        renderPDF.drawToFile(drawing, f"results/{week_n}.pdf")

    # Merge all pdfs into one
    import PyPDF2

    merger = PyPDF2.PdfMerger()

    for i in range(len(weeks)):
        merger.append(f"results/{i}.pdf", "rb")

    merger.write("results/result.pdf")
