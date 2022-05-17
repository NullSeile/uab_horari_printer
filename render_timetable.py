import os
import shutil
from typing import Dict, List
import drawSvg as draw
from svglib.svglib import svg2rlg, register_font
from reportlab.graphics import renderPDF

from utils import MONTH_NAME, HolidayType, Subject, SubjectProps, SubjectType, Week


def render_to_pdf(weeks: List[Week], subjects_props: Dict[str, SubjectProps]):

    register_font("calibri", "calibri_bold.ttf", "bold")

    n_hours = 11  # From 9 to 20
    first_hour = 9

    width = 1000.0
    height = 500.0

    hour_label_width = width * 0.05
    day_label_height = height / (n_hours + 1)

    work_width = width - hour_label_width
    work_height = height - day_label_height
    day_width = work_width / 5
    day_height = work_height / n_hours

    text_size = day_height * 0.3

    light_line_width = height / 1000
    dark_line_width = 2 * light_line_width

    def get_day_x(day):
        return hour_label_width + day_width * day

    def get_hour_y(hour):
        return height - day_label_height - day_height - (hour - first_hour) * day_height

    # Create path to save the files
    if os.path.exists("results"):
        shutil.rmtree("results")
    os.mkdir("results")

    if os.path.exists("temp"):
        shutil.rmtree("temp")
    os.mkdir("temp")

    for week_n, week in enumerate(weeks):

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
                        height - day_label_height,
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
                        text += f" Se{s.group}"
                    elif s.type == SubjectType.PROBLEMS:
                        text += f" Pb{s.group}"
                    elif s.type == SubjectType.LABORATORY:
                        text += f" Pr{s.group}"
                    elif s.type == SubjectType.EXAM:
                        text += f" {s.group} Examen"
                    elif s.type == SubjectType.UNKNOWN:
                        text += f" {s.group} (??)"

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
                            y + day_height / 2,
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
            y = day_height * (i + 1)
            d.append(
                draw.Line(0, y, width, y, stroke="black", stroke_width=light_line_width)
            )

        d.append(
            draw.Line(
                0,
                height - day_label_height,
                width,
                height - day_label_height,
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
                    f"{day.date.day}-{MONTH_NAME[day.date.month-1]}",
                    text_size,
                    day_x + day_width / 2,
                    height - day_label_height / 2,
                    center=True,
                    fill="black",
                    font_weight="bold",
                    font_family="calibri",
                )
            )

        # Draw hours (only one time)
        for hour in range(first_hour, first_hour + n_hours):
            day_y = get_hour_y(hour)
            d.append(
                draw.Text(
                    f"{hour}-{hour+1}",
                    text_size,
                    hour_label_width / 2,
                    day_y + day_height / 2,
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
                        0,
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
                        work_height / 2,
                        center=True,
                        fill="black",
                        font_weight="bold",
                        font_family="calibri",
                    )
                )

        with open(f"temp/{week_n}.svg", "w", encoding="utf8") as file:
            d.asSvg(outputFile=file)

        drawing = svg2rlg(f"temp/{week_n}.svg")
        renderPDF.drawToFile(drawing, f"results/{week_n}.pdf")

    # Merge all pdfs into one
    import PyPDF2

    merger = PyPDF2.PdfFileMerger()

    for i in range(len(weeks)):
        merger.append(f"results/{i}.pdf", "rb")

    merger.write("results/result.pdf")
