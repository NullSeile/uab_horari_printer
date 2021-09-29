from bs4 import BeautifulSoup
import bs4.element
import re
from enum import IntEnum
import drawSvg as draw
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import os
import shutil
from svglib.svglib import svg2rlg, register_font
from reportlab.graphics import renderPDF
import datetime

from typing import List, Dict, Union


class SubjectProps:
	def __init__(self, name: str, color: str):
		self.name = name
		self.color = color

# Which month and year you want to generate
starting_month = 9
starting_year = 2021

# How many weeks
number_of_weeks = 18

# If you want to skip any starting week
weeks_to_skip = 1

# Which subjects to get (short name and color)
SUBJECT_PROPS = {
	'100095': SubjectProps('GL',  '#ffd28a'),
	'100098': SubjectProps('SMD', '#afeeee'),
	'100096': SubjectProps('EA',  '#e9ffa4'),
	'100099': SubjectProps('TM',  '#ffb3ad'),
	'100087': SubjectProps('FVR', '#aba6ff'),
}

# SUBJECT_PROPS = {
# 	# '100095': SubjectProps('GL',  '#ffd28a'),
# 	'100088': SubjectProps('ALG', '#afeeee'),
# 	'100090': SubjectProps('FIS',  '#ffd28a'),
# 	# '100090': SubjectProps('FIS',  '#e9ffa4'),
# 	# '100099': SubjectProps('TM',  '#ffb3ad'),
# 	'100087': SubjectProps('FVR', '#aba6ff'),
# }

# Courses to get the data from
courses = ['CURS - 1', 'CURS - 2']


################################
# Get the data from the website
################################

results = ['<div class="fc-event-container">\n'] * number_of_weeks
starting_day = None

driver = webdriver.Chrome()
for course in courses:
	
	driver.get("https://web1.uab.es:31501/pds/consultaPublica/look%5Bconpub%5DInicioPubHora?entradaPublica=true&idioma=ca&pais=ES")
	
	select = Select(driver.find_element_by_id('centro'))
	select.select_by_visible_text("103 - Facultat de Ciències")
	
	select = Select(driver.find_element_by_id('curso'))
	select.select_by_visible_text(course)
	
	driver.find_element_by_id('buscarCalendario').click()
	
	# Force starting at start of the requested month and year
	driver.find_element_by_id('comboMesesAnyos').click()
	driver.find_element(By.CSS_SELECTOR, f'option[value="9/2021"]').click()
	WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event-container')))
	
	driver.find_element_by_id('comboMesesAnyos').click()
	driver.find_element(By.CSS_SELECTOR, f'option[value="10/2021"]').click()
	WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event-container')))
	
	driver.find_element_by_id('comboMesesAnyos').click()
	driver.find_element(By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]').click()
	WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event-container')))
	
	# Skip the first `weeks_to_skip` weeks
	for i in range(weeks_to_skip):
		driver.find_element_by_class_name('fc-button-next').click()
		WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event-container')))
	
	# Get the starting day
	starting_day = int(driver.find_element_by_class_name('fc-header-title').text[:2])
	
	for i in range(number_of_weeks):
		
		try:
			WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event')))
			
			for event in driver.find_elements_by_class_name('fc-event'):
				results[i] += event.get_attribute('outerHTML') + '\n'
			
		except TimeoutException:
			print(f"WARNING: No events in week {i}")
		
		driver.find_element_by_class_name('fc-button-next').click()


for result in results:
	result += "</div>"

driver.close()


#####################################################
# Parse the data collected from the website into a
# manejable format for drawing and draw it to a svg
#####################################################

class SubjectType(IntEnum):
	UNKNOWN = -1
	THEORY = 0
	SEMINAR = 1
	PROBLEMS = 2
	LABORATORY = 3
	EXAM = 4
	
	def __str__(self):
		return self.name
	
class HolidayType(IntEnum):
	FESTIU = 0
	NO_LECTIU = 1


# Stores information of a subject
class Subject:
	def __init__(self):
		self.id: str = None
		self.group: str = None
		self.type: SubjectType = None
		self.classroom: str = None
	
	def __str__(self):
		return f"{SUBJECT_PROPS[self.id].name}: {self.group} - {self.type} at {self.classroom}"
	
	def __repr__(self):
		return f"Subject({self})"


class Day:
	def __init__(self):
		self.hours: Dict[int, List[Subject]] = dict() # key = hour, value = ubject
		self.holiday: Union[None, HolidayType] = None
		self.date: datetime.date = None
		
	def add_subject(self, hour, subject):
		if hour not in self.hours.keys():
			self.hours[hour] = list()
		
		self.hours[hour].append(subject)
	
	def __str__(self):
		return f"holiday={self.holiday} {self.hours}"

class Week:
	def __init__(self, date: datetime.date):
		self.days = {
			0: Day(), # Monday
			1: Day(), # Tuesday
			2: Day(), # Wednesday
			3: Day(), # Thursday
			4: Day(), # Friday
		}
		for day_n, day in self.days.items():
			day.date = date + datetime.timedelta(days=day_n)
	
	def __getitem__(self, day):
		assert 0 <= day < 5, "Day must be a number between 0 and 4"
		return self.days[day]
		

# Get the screen position from an event and output its day
def get_day_from_event(event):

	# Position in the screen of each day
	WEEKDAYS_X = [
		62,
		207,
		351,
		495,
		639,
		779 # Saturday
	]
	
	position = float(re.search('(?<=left: ).*?(?=px;)', event.get('style')).group(0))
	
	for i in range(5):
		if WEEKDAYS_X[i] <= position < WEEKDAYS_X[i + 1]:
			return i
	
	raise ValueError(f"{event} does not fit in any day")


# Create path to save the files
if os.path.exists('results'):
	shutil.rmtree('results')
os.mkdir('results')

if os.path.exists('temp'):
	shutil.rmtree('temp')
os.mkdir('temp')


# Month number to month name
MONTHS = [
	'gen', 'febr', 'març', 'abr', 'maig', 'juny', 'jul', 'ago', 'set', 'oct', 'nov', 'des'
]

register_font('calibri', 'calibri_bold.ttf', 'bold')

# Will store all weeks
weeks: List[Week] = list()

date = datetime.date(starting_year, starting_month, starting_day)
for week_n, result in enumerate(results):
	
	week = Week(date)
	
	parsed = BeautifulSoup(result, 'html.parser')
	
	# For each event in the week
	event: bs4.element.Tag
	for event in parsed.select('div[class*="fc-event fc-event-vert fc-event-start fc-event-end"]'):
		
		content = event.find('div', {'class': 'fc-event-title'})
		day_n = get_day_from_event(event)
		
		# Check if it's holiday
		if content.getText() == "Dia festiu":
			week[day_n].holiday = HolidayType.FESTIU
	
		elif content.getText() ==  "Dia no lectiu":
			week[day_n].holiday = HolidayType.NO_LECTIU
		
		else:
			content = str(content.find('p'))
			subject_id = re.search('(?<=<p>).*?(?= -)', content).group(0)
			
			if subject_id in SUBJECT_PROPS.keys():
				
				subject = Subject()
				
				subject.id = subject_id
				
				# Get the group
				group_text = re.search('(?<=Grup ).*?(?=<br/>)', content).group(0)
				subject.group = group_text[:group_text.find(' - ')]
				
				# Get the subject type
				type_text = group_text[group_text.find(' - ')+3:]
				if type_text == 'Teoria':
					subject.type = SubjectType.THEORY
				elif type_text == "Pràctiques d'Aula":
					subject.type = SubjectType.PROBLEMS
				elif type_text == "Pràctiques de Laboratori":
					subject.type = SubjectType.LABORATORY
				elif type_text == "Seminaris":
					subject.type = SubjectType.SEMINAR
				elif type_text == "Examen":
					subject.type = SubjectType.EXAM
				else:
					subject.type = SubjectType.UNKNOWN
					print(f"ERROR: {event} has not valid type '{type_text}'")
				
				# Get the classroom
				classroom = re.search('(?<=Aula ).*?(?= -)', content)
				if classroom is not None:
					subject.classroom = classroom.group(0)
				else:
					subject.classroom = ''
			
				# Get the hour
				hours = str(event.find('div', {'class': 'fc-event-time'}).contents[0])
				
				start_time = int(hours[:2])
				end_time = int(hours[8:10])
				
				# Add the Subject
				for h in range(start_time, end_time):
					
					week[day_n].add_subject(h, subject)
	
	weeks.append(week)
	date += datetime.timedelta(weeks=1)
	

#########################################
# Draw the collected data into a svg
#########################################

n_hours = 11 # From 9 to 20
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

for week_n, week in enumerate(weeks):
	
	d = draw.Drawing(width, height)
	
	d.append(draw.Rectangle(0, 0, width, height, fill='white', stroke='black', stroke_width=dark_line_width)) # Background
	
	# For each day get the subjects (data)
	for day_n, day in week.days.items():
		
		day_x = get_day_x(day_n)
		
		# Draw gray background on the day label
		if day.holiday is not None:
			d.append(draw.Rectangle(
				day_x,
				height - day_label_height,
				day_width,
				day_height,
				fill='#BEBEBE',
				stroke='black',
				stroke_width='0.2'
			))
		
		for hour, subjects in day.hours.items():
			y = get_hour_y(hour)
			
			s: Subject
			for i, s in enumerate(subjects):
				
				new_width = day_width / len(subjects)
				
				x = day_x + i * new_width
				
				props = SUBJECT_PROPS[s.id]
				
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
				
				d.append(draw.Rectangle(
					x,
					y,
					new_width,
					day_height,
					fill=props.color,
					stroke='black',
					stroke_width=dark_line_width
				))
				
				d.append(draw.Text(
					text,
					text_size,
					x + new_width / 2,
					y + day_height / 2,
					center=True,
					fill='black',
					font_weight='bold',
					font_family='calibri'
				))
	
	# Draw grid
	for i in range(1, 5):
		x = hour_label_width + (day_width * i)
		d.append(draw.Line(x, 0, x, height, stroke='black', stroke_width=light_line_width))
	
	for i in range(n_hours-1):
		y = day_height * (i+1)
		d.append(draw.Line(0, y, width, y, stroke='black', stroke_width=light_line_width))
	
	d.append(draw.Line(0, height - day_label_height, width, height - day_label_height, stroke='black', stroke_width=dark_line_width))
	d.append(draw.Line(hour_label_width, 0, hour_label_width, height, stroke='black', stroke_width=dark_line_width))
	
	# Draw day and month text on top
	for day_n, day in week.days.items():
		day_x = get_day_x(day_n)
		d.append(draw.Text(
			f"{day.date.day}-{MONTHS[day.date.month-1]}",
			text_size,
			day_x + day_width / 2,
			height - day_label_height / 2,
			center=True,
			fill='black',
			font_weight='bold',
			font_family='calibri'
		))
		
	# Draw hours (only one time)
	for hour in range(first_hour, first_hour + n_hours):
		day_y = get_hour_y(hour)
		d.append(draw.Text(
			f"{hour}-{hour+1}",
			text_size,
			hour_label_width / 2,
			day_y + day_height / 2,
			center=True,
			fill='black',
			font_weight='bold',
			font_family='calibri'
		))
	
	# Draw holidays as gray
	for day_n, day in week.days.items():
		if day.holiday is not None:
			day_x = get_day_x(day_n)
			d.append(draw.Rectangle(
				day_x,
				0,
				day_width,
				work_height,
				fill='#BEBEBE',
				stroke='black',
				stroke_width='0.2'
			))
	
			holiday_text = None
			if day.holiday == HolidayType.FESTIU:
				holiday_text = 'FESTIU'
			elif day.holiday == HolidayType.NO_LECTIU:
				holiday_text = 'NO LECTIU'
			else:
				holiday_text = 'FESTA??'
	
			d.append(draw.Text(
				holiday_text,
				text_size,
				day_x + day_width / 2,
				work_height / 2,
				center=True,
				fill='black',
				font_weight='bold',
				font_family='calibri'
			))
	
	with open(f'temp/{week_n}.svg', 'w', encoding='utf8') as file:
		d.asSvg(outputFile=file)
	
	drawing = svg2rlg(f'temp/{week_n}.svg')
	renderPDF.drawToFile(drawing, f'results/{week_n}.pdf')


# Merge all pdfs into one
import PyPDF2
merger = PyPDF2.PdfFileMerger()

for i in range(number_of_weeks):
	merger.append(f'results/{i}.pdf', 'rb')

merger.write('results/result.pdf')
