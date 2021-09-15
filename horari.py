from bs4 import BeautifulSoup
import bs4.element
import re
from enum import IntEnum
import drawSvg as draw
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import shutil
from svglib.svglib import svg2rlg, register_font
from reportlab.graphics import renderPDF
import datetime

# Which month and year you want to generate
starting_month = 9
starting_year = 2021

# How many weeks
number_of_weeks = 18

# Which subjects to get (short name and color)
SUBJECT_PROPS = {
	'100095': {'short': 'GL', 'color': '#F9BF94'},
	'100098': {'short': 'SMD', 'color': '#95B4D5'},
	'100096': {'short': 'EA', 'color': '#B3A2C7'},
	'100099': {'short': 'TM', 'color': '#FAC090'},
	'100087': {'short': 'FVR', 'color': '#FFFF99'},
}

# SUBJECT_PROPS = {
# 	'100087': {'short': 'FVR', 'color': '#B3A2C7'},
# 	'100088': {'short': 'ALG', 'color': '#C3D69B'},
# 	'100089': {'short': 'FM', 'color': '#FFFF99'},
# 	'100090': {'short': 'FIS', 'color': '#FAC090'},
# 	'100091': {'short': 'EIM', 'color': '#95B3D7'},
# 	'100092': {'short': 'TCA', 'color': '#F79646'},
# }

# Courses to get the data from
courses = ['CURS - 1', 'CURS - 2']

# Month number to month name
MONTHS = [
	'gen', 'febr', 'març', 'abr', 'maig', 'juny', 'jul', 'ago', 'set', 'oct', 'nov', 'des'
]


################################
# Get the data from the website
################################

results = ['<div class="fc-event-container" style="position:absolute;z-index:8;top:0;left:0">\n'] * number_of_weeks
starting_day = None

driver = webdriver.Chrome()
for course in courses:

	driver.get("https://web1.uab.es:31501/pds/consultaPublica/look%5Bconpub%5DInicioPubHora?entradaPublica=true&idioma=ca&pais=ES")
	
	select = Select(driver.find_element_by_id('centro'))
	select.select_by_visible_text("103 - Facultat de Ciències")
	
	select = Select(driver.find_element_by_id('curso'))
	select.select_by_visible_text(course)
	
	driver.find_element_by_id('buscarCalendario').click()
	
	driver.find_element_by_id('comboMesesAnyos').click()
	driver.find_element(By.CSS_SELECTOR, f'option[value="{starting_month}/{starting_year}"]').click()
	
	# Get the starting day
	starting_day = int(driver.find_element_by_class_name('fc-header-title').text[:2])
	
	for i in range(number_of_weeks):
	
		WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'fc-event-container')))
		
		for event in driver.find_elements_by_class_name('fc-event'):
			results[i] += event.get_attribute('outerHTML') + '\n'
		
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
	def __init__(self, id: str, group: str, type: SubjectType, classroom: str):
		self.id = id
		self.group = group
		self.type = type
		self.classroom = classroom
	
	def __str__(self):
		return f"{SUBJECT_PROPS[self.id]['short']}: {self.group} - {self.type} at {self.classroom}"
	
	def __repr__(self):
		return f"Subject({self})"


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


register_font('calibri', 'calibri_bold.ttf', 'bold')

date = datetime.date(starting_year, starting_month, starting_day)

for week_n, result in enumerate(results):
	
	#############################################
	# Make a table of every subject of the week
	#############################################
	
	# Stores which subjects occurred in hour of each day
	table = {
		0: dict(), # Monday
		1: dict(), # Tuesday
		2: dict(), # Wednesday
		3: dict(), # Thursday
		4: dict(), # Friday
	}
	
	# Which days of the week are holidays (no lectiu o festiu)
	holidays = dict()
	
	parsed = BeautifulSoup(result, 'html.parser')
	
	# For each event in the week
	event: bs4.element.Tag
	for event in parsed.select('div[class*="fc-event fc-event-vert fc-event-start fc-event-end"]'):
		
		content = event.find('div', {'class': 'fc-event-title'})
		
		# Check if it's holiday (then skip everything else)
		if content.getText() == "Dia festiu":
			day = get_day_from_event(event)
			holidays[day] = HolidayType.FESTIU
			continue
	
		elif content.getText() ==  "Dia no lectiu":
			day = get_day_from_event(event)
			holidays[day] = HolidayType.NO_LECTIU
			continue
		
		
		content = str(content.find('p'))
		subject_id = re.search('(?<=<p>).*?(?= -)', content).group(0)
		
		if subject_id in SUBJECT_PROPS.keys():
			
			hours = str(event.find('div', {'class': 'fc-event-time'}).contents[0])
			
			start_time = int(hours[:2])
			end_time = int(hours[8:10])
			
			group_text = re.search('(?<=Grup ).*?(?=<br/>)', content).group(0)
			
			group = group_text[:group_text.find(' - ')]
			type_text = group_text[group_text.find(' - ')+3:]
			
			subject_type = None
			if type_text == 'Teoria':
				subject_type = SubjectType.THEORY
			elif type_text == "Pràctiques d'Aula":
				subject_type = SubjectType.PROBLEMS
			elif type_text == "Pràctiques de Laboratori":
				subject_type = SubjectType.LABORATORY
			elif type_text == "Seminaris":
				subject_type = SubjectType.SEMINAR
			elif type_text == "Examen":
				subject_type = SubjectType.EXAM
			else:
				subject_type = SubjectType.UNKNOWN
				print(f"ERROR: {event} has not valid type {type_text}")
			
			
			classroom = re.search('(?<=Aula ).*?(?= -)', content)
			if classroom is not None:
				classroom = classroom.group(0)
			else:
				classroom = ''
			
			day = get_day_from_event(event)
			
			for h in range(start_time, end_time):
				if h not in table[day].keys():
					table[day][h] = list()
				
				table[day][h].append(Subject(subject_id, group, subject_type, classroom))
	
	
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
	
	d = draw.Drawing(width, height)
	
	d.append(draw.Rectangle(0, 0, width, height, fill='white', stroke='black', stroke_width=dark_line_width)) # Background
	
	def get_day_x(day):
		return hour_label_width + day_width * day
	
	# For each day get the subjects (data)
	for day, data in enumerate(table.values()):
		
		day_x = get_day_x(day)
		
		# Draw gray background on the day label
		if day in holidays.keys():
			d.append(draw.Rectangle(
				day_x,
				height - day_label_height,
				day_width,
				day_height,
				fill='#BEBEBE',
				stroke='black',
				stroke_width='0.2'
			))
		
		# Draw day and month text on top
		d.append(draw.Text(
			f"{date.day}-{MONTHS[date.month-1]}",
			text_size,
			day_x + day_width / 2,
			height - day_label_height / 2,
			center=True,
			fill='black',
			font_weight='bold',
			font_family='calibri'
		))
		
		date += datetime.timedelta(days=1)
		
		for hour in range(first_hour, first_hour + n_hours):
			
			y = height - day_label_height - day_height - (hour - first_hour) * day_height
			
			# Draw hours (only one time)
			if day == 0:
				d.append(draw.Text(
					f"{hour}-{hour+1}",
					text_size,
					hour_label_width / 2,
					y + day_height / 2,
					center=True,
					fill='black',
					font_weight='bold',
					font_family='calibri'
				))
			
			if hour in data.keys():  # If there are any subjects in the hour
				subjects = data[hour]
				
				s: Subject
				for i, s in enumerate(subjects):
					
					new_width = day_width / len(subjects)
					
					x = day_x + i * new_width
					
					props = SUBJECT_PROPS[s.id]
					
					text = props['short']
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
						fill=props['color'],
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
	
	# Draw holidays as gray
	for day in holidays.keys():
		day_x = get_day_x(day)
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
		if holidays[day] == HolidayType.FESTIU:
			holiday_text = 'FESTIU'
		elif holidays[day] == HolidayType.NO_LECTIU:
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
	
	# Skip the weekend
	date += datetime.timedelta(days=2)


# Merge all pdfs into one
import PyPDF2
merger = PyPDF2.PdfFileMerger()

for i in range(number_of_weeks):
	merger.append(f'results/{i}.pdf', 'rb')

merger.write('results/result.pdf')
