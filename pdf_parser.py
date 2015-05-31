from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdftypes import PDFStream, PDFObjRef, resolve1, stream_value
from pdfminer.layout import LAParams, LTChar, LTTextBox, LTTextLine, LTFigure, LTTextBoxHorizontal, LTLine 
from dateutil.parser import *
import sys
import re
import xml.etree.ElementTree as ET
import unicodedata
import calendar
import inflect
from HTMLParser import HTMLParser


def parse_layout(layout):
        #"""Function to recursively parse the layout tree."""
        for lt_obj in layout:
                #print lt_obj.text, 
                #print lt_obj
##                x0 = lt_obj.bbox[0]
##                print 'x0:' + x0
##                x1 = lt_obj.bbox[2]
##                print 'x1:' + x1
##                #print(lt_obj.__class__.__name__)
                #print(lt_obj.bbox)
                #print lt_obj.get_text() 
                if isinstance(lt_obj, LTFigure):
                        #print(lt_obj.__class__.__name__)
                        #parse_layout(lt_obj)  # Recursive
                        populate_lines(lt_obj)
##                elif isinstance(lt_obj,LTLine):
##                        line_count=line_count+1
##                        break
##                elif isinstance(lt_obj, LTChar):
##                        (a,b,c,d,e,f) = lt_obj.matrix
##                        print f
                
        #print text, line_count

def populate_lines(text_container):
        
        curr_y = 0
        for lt_obj in text_container:
                
                if isinstance(lt_obj,LTChar):
                        (a,b,c,d,e,f) = lt_obj.matrix
                        #print f, curr_y, lt_obj.get_text()
                        if f != curr_y:
                                if abs(f-curr_y) < 10:#Handling superscript th
                                        lines[len(lines)-1] = lines[len(lines)-1] + lt_obj.get_text()
                                else:
                                        curr_y = f
                                        lines.append(''+lt_obj.get_text())
                        else:
                                lines[len(lines)-1] = lines[len(lines)-1] + lt_obj.get_text()
        for index, line in enumerate(lines):
                if isinstance(line,unicode):
                        lines[index] = unicodedata.normalize('NFKD', line).encode('ascii','ignore')
                        
def parse_pdf(file_name):
    # Open a PDF file.
    fp = open(file_name, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fp)
    # Create a PDF document object that stores the document structure.
    # Supply the password for initialization.
    document = PDFDocument(parser)
    # Check if the document allows text extraction. If not, abort.
    if not document.is_extractable:
        raise PDFTextExtractionNotAllowed
    # Create a PDF resource manager object that stores shared resources.
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams()
    #Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    for page in PDFPage.create_pages(document):
            if page.pageid == 3 or page.pageid==5 or page.pageid!=0:
                    #print (page.pageid - 1)/2
                    interpreter.process_page(page)
                    layout = device.get_result()
                    parse_layout(layout)
    

def addCoram(case,judgeText,positionText):
        judge = ET.Element('Judge')
        judge.text= judgeText
        if positionText == "":
                positionText = "NA"
                
        judge.set('Position',positionText)
        if case.find('CoramGroup') is None:
                CoramGroup = ET.Element('CoramGroup')
                CoramGroup.append(judge)
                case.append(CoramGroup)
        else:
                case.find('CoramGroup').append(judge)
        return case

def addDate(case, month, day, year, type):
        p = inflect.engine()
        date = ET.Element('Date')
        date.set('Month',month)
        date.set('Date',str(day))
        date.set('Year',str(year))
        date.set('Type',type)
        date.text = p.ordinal(day) + " " + month + " " +str(year)
        case.append(date)
        return case

def addCourtName(case,name):
        court = ET.Element('Court')
        courtname = ET.Element('CourtName')
        courtname.text=name
        court.append(courtname)
        case.append(court)
        return case
def getPetitioner(versus_found_at,lines):
        p= inflect.engine()
        i = versus_found_at - 1
        petitioners_text = ''
        petitioner={}
        while i > 0:
                if 'PETITION' in lines[i] or 'SUIT' in lines[i] or 'matter between' in lines[i]:
                        break
                petitioners_text =  lines[i] + petitioners_text
                i-=1
        match = re.search('petitioner[s]?|plaintiff[s]?',petitioners_text,re.I)
        petitioner_type = petitioners_text[match.start():match.end()]
        petitioner_type = p.singular_noun(petitioner_type) if  p.singular_noun(petitioner_type) else petitioner_type
        petitioner['petitioner_type'] = petitioner_type.title()
        
        party_name_match1 = re.search('[.]{3,4}',petitioners_text,re.I)
        party_name = petitioners_text[:party_name_match1.start()]
        party_name_match2 = re.search('through|[sw]/o',petitioners_text,re.I)
        if party_name_match2 is not None:
                petitioner['party_name'] = party_name[:party_name_match2.start()].replace(",","").strip()
        else:
                petitioner['party_name'] = party_name
        return petitioner
        

def getRespondents(versus_found_at,lines):
        i = versus_found_at + 1
        respondents_text = ''
        no_of_respondents = 0
        counsel_found_at = 0
        respondents_list = []
        p= inflect.engine()
        while i > 0:
                match = re.search('defendant[s]?|respondent[s]?',lines[i],re.I)
                if match is not None:
                        no_of_respondents += 1
                        prev_length = len(respondents_text)
                        respondent_type = lines[i][match.start():match.end()]
                        respondent_type = p.singular_noun(respondent_type) if  p.singular_noun(respondent_type) else respondent_type
                        #print type
                        respondents_text =  respondents_text + lines[i]
                        if no_of_respondents == 1:
                                respondent={}
                                respondent['party_name']=respondents_text[:respondents_text.find("...")]
                                respondent['respondent_type'] = respondent_type
                                respondents_list.append(respondent)
                                #addRespondent(case,respondents_text[:respondents_text.find("...")],respondent_type)
                        else:
                                #pattern_respondents_multiple = re.compile(r'\d{1}[\]{1}].+[.]',re.I)
                                match_list = re.finditer(r'\d{1}\]{1}([^.]+)[.]',respondents_text,re.I)
                                #print len(list_respondents)
                                for match in match_list:
                                        respondent={}
                                        respondent['party_name']=match.group(1)
                                        respondent['respondent_type'] = respondent_type
                                        respondents_list.append(respondent)
                                        #case = addRespondent(case,match.group(1),respondent_type)
                        counsel_found_at = i+1
                        break
                respondents_text =  respondents_text + lines[i]
                no_of_respondents += 1
                i+=1
        return respondents_list,counsel_found_at

def addPetitioner(tree,party_name, petitioner_type):
        petitioner = ET.Element('Petitioner')
        case = tree.getroot()
        if case is None:
                print "hihihi"
        
        petitioner.text= party_name
        petitioner.set('Type',petitioner_type)
        if tree.find('.//PetitionerGroup') is None:
                PetitionerGroup = ET.Element('PetitionerGroup')
                PetitionerGroup.append(petitioner)
                if tree.find('.//Parties') is None:
                        parties = ET.Element('Parties')
                        parties.append(PetitionerGroup)
                        if tree.find('.//PartiesGroup') is None:
                                PartiesGroup = ET.Element('PartiesGroup')
                                PartiesGroup.append(parties)
                                case.append(PartiesGroup)
                        else:
                                tree.find('.//PartiesGroup').append(parties)
                                #case.append(PartiesGroup)
                else:
                        tree.find('.//Parties').append(PetitionerGroup)
        else:
                tree.find('.//PetitionerGroup').append(petitioner)
        return tree
def addRespondent(tree,party_name, respondent_type):
        respondent = ET.Element('Respondent')
        case = tree.getroot()
        if case is None:
                print "hihihi"
        #ET.dump(case)
        #parser = HTMLParser()
        #party_name = parser.unescape(party_name)
        respondent.text= party_name
        respondent.set('Type',respondent_type)
        if tree.find('.//RespondentGroup') is None:
                RespondentGroup = ET.Element('RespondentGroup')
                RespondentGroup.append(respondent)
                if tree.find('.//Parties') is None:
                        parties = ET.Element('Parties')
                        parties.append(RespondentGroup)
                        if tree.find('.//PartiesGroup') is None:
                                PartiesGroup = ET.Element('PartiesGroup')
                                PartiesGroup.append(parties)
                                case.append(PartiesGroup)
                        else:
                                tree.find('.//PartiesGroup').append(parties)
                                #case.append(PartiesGroup)
                else:
                        tree.find('.//Parties').append(RespondentGroup)
        else:
                tree.find('.//RespondentGroup').append(respondent)
        return tree

def addCounselGroup(tree,counsel_group):
        for_petitioners = counsel_group['for_petitioners']
        for_respondents = counsel_group['for_respondents']
        
        case = tree.getroot()
        if case is None:
                print "No Root Found"
        
        CounselGroup = ET.Element('CounselGroup')
        forPetitioner = ET.Element('forPetitioner')
        forRespondent = ET.Element('forRespondent')

        for pet in for_petitioners:
                CounselName = ET.Element('CounselName')
                CounselName.text=pet.strip()
                forPetitioner.append(CounselName)
        CounselGroup.append(forPetitioner)
        for res in for_respondents:
                CounselName = ET.Element('CounselName')
                CounselName.text=res.strip()
                forRespondent.append(CounselName)
        CounselGroup.append(forRespondent)
        case.append(CounselGroup)
        tree._setroot(case)
        return tree
def getCounselGroup(index,lines):
        i = index
        for_petitioner_text=''
        petitioner_done = 0
        for_petitioners = []
        for_petitioner_pattern = re.compile(r'for\s*?(the)?\s*?(applicant/plaintiff)?(petitioners{0,1})?[.]$',re.I)
        for_respondent_pattern = re.compile(r'for\s*?(the)?\s*?(defendant)?(respondents{0,1})?[.]?',re.I)
        for_respondent_text=''
        respondent_done = 0
        for_respondents = []
        while respondent_done != 1:
                
                if re.search('[a-z\s]*',lines[i],re.I) is not None and petitioner_done != 1:
                        for_petitioner_text+=lines[i]
                        for_petitioner_match = re.search(for_petitioner_pattern,for_petitioner_text)
                        if for_petitioner_match is not None:
                                petitioner_done = 1
                                petitioner_line = for_petitioner_text[:for_petitioner_match.start()]
                                petitioner_line_match = re.search(r'\b(along with)|(a/w)|(h/f)\b',petitioner_line,re.I)
                                if petitioner_line_match is not None:
                                        for_petitioners.append(re.search(r'^[.]{0,}([.a-z\s]+)[,]',petitioner_line[:petitioner_line_match.start()],re.I).group(1))
                                        for match_obj in re.finditer(r'[.]{0,}([.a-z\s]+)[,]|(and)',petitioner_line[petitioner_line_match.end():],re.I):
                                                if ' and ' in match_obj.group(1):
                                                        for_petitioners.append(match_obj.group(1).split(' and ')[0])
                                                        for_petitioners.append(match_obj.group(1).split(' and ')[1])
                                                        break

                                                for_petitioners.append(match_obj.group(1))
                                        
                                        
                                
                elif re.search('[a-z\s]*',lines[i],re.I) is not None and petitioner_done == 1 and respondent_done != 1:
                        for_respondent_text+=lines[i]
                        for_respondent_match = re.search(for_respondent_pattern,for_respondent_text)
                        if for_respondent_match is not None:
                                respondent_done = 1
                                respondent_line = for_respondent_text[:for_respondent_match.start()]
                                respondent_split_items =  re.split(r'along with|a/w[.]',respondent_line)
                                for item in respondent_split_items:
                                        for_respondents.append(re.search(r'^[.\s]{0,}([.a-z\s]+)[,]',item,re.I).group(1))
                                        
                                                
                i=i+1
        counsel_group={}
        counsel_group['for_petitioners'] = for_petitioners
        counsel_group['for_respondents'] = for_respondents                

        return counsel_group
                


def getActElement(title):
        Act = ET.Element('Act')
        Title = ET.Element('Title')
        id=""
        for word in title.split(" "):
                if word != "and" and word != "&":
                        if word.isdigit():
                                id = id + "-"
                                id = id + str(word)
                        else:
                                id = id + word[:1]
        
        Title.text = title
        Title.set("id",id)
        Act.append(Title)
        return Act
def addSecRef(tree,section):
        case = tree.getroot()
        if case is None:
                print "No Root Found"
        
        Title = ET.Element('Title')
        id= tree.find('.//Act/Title').attrib['id'] + "-" +section
        Title.text = section
        Title.set("id",id)
        if tree.find('.//SecRef') is None:
                SecRef = ET.Element('SecRef')
                SecRef.append(Title)
                tree.find('.//Para').append(SecRef)
        else:
                tree.find('.//SecRef').append(Title)

        return tree
        
def addJudgmentGroup(tree, section_starts_at, lines):
        
        judgment_group_title  = [x for x in re.search(r'(judgment)?(order)?(p.c.)?',lines[index],re.I).groups() if x is not None][0]
        case = tree.getroot()
        if case is None:
                print "No Root Found"
        
        JudgmentGroup = ET.Element('JudgmentGroup')
        JudgmentGroup.set('Title',judgment_group_title)
        

        Para = ET.Element('Para')

        #section_text_content=''
        i=section_starts_at
        section_set = set()
        section_list=[]
        while i < len(lines):
                act_match = re.search(r'(Act,)',lines[i])
                section_match = re.search(r'(Section[s]?)',lines[i])

                if act_match is not None:
                        act_line = lines[i-1]+lines[i]+lines[i+1]
                        #print act_line
                        act_match_iter = re.finditer(r'([A-Z][a-z]+\s+[&]?\s?(and)?\s?){1,}(Act,)\s+\d{4}',act_line)
                        for full_act_match in list(act_match_iter):
                                if full_act_match is not None:
                                        Para.append(getActElement(full_act_match.group(0)))
                if section_match is not None:
                        section_line = lines[i-1]+lines[i]+lines[i+1]
                        section_matches = re.findall(r'Section\s+\d+\s+[()\d\s]{0,}',section_line)
                        for section_match in section_matches:
                                sum=0
                                for c in section_match:
                                        if c is '(' or c is ')':
                                                sum += 1
                                        
                                if sum == 1 or sum == 3:
                                        print section_line[section_line.find(section_match):section_line.find(section_match)+len(section_match)+3].split(" ",1)[1].replace(" ","").replace(",","")
                                        section_list.append(section_line[section_line.find(section_match):section_line.find(section_match)+len(section_match)+3].split(" ",1)[1].replace(" ","").replace(",",""))
                                        
                                else:
                                        print section_match.split(" ",1)[1].replace(" ","").replace(",","")
                                        section_list.append(section_match.split(" ",1)[1].replace(" ","").replace(",",""))
                        #sections_matches = re.findall(r'Sections\s+\d+\s+[()\d\s]{0,}',section_line)
                        #print section_line + "\n"
                        
                i+=1

        section_set.update(section_list)
        #for section in section_set:
                
        print section_set

        #print section_text_content
        JudgmentGroup.append(Para)
        case.append(JudgmentGroup)
        tree._setroot(case)
        for section in section_set:
                if section is not "":
                        tree = addSecRef(tree,section)
                        
                
        return tree
        
        
for arg in sys.argv[1:]:
        lines = []
        parse_pdf(arg)
        coram_found_at=0
        coram_found=0
        court_name_found=0
        counsel_found_at=0
        versus_found=0
        XMLTree = ET.ElementTree()
        case = ET.Element('case')
        XMLTree._setroot(case)
        pattern_court_name = re.compile(r'\s{0,}in\s{0,}the\s{0,}high\s{0,}court\s{0,}of\s{0,}judicature\s{0,}(\S+)\s{0,}([a-zA-Z]*)\s{0,}', re.IGNORECASE)
        pattern_coram = re.compile(r'coram\s{0,}:\s{0,}([a-zA-Z.\s]*)[,]?([\sJ.]*)', re.IGNORECASE)
        pattern_coram_next = re.compile(r'\s{0,}&\s{0,}([a-zA-Z.\s]*)[,]?([\sJ.]*)', re.IGNORECASE)
        pattern_versus = re.compile(r'\s{0,}v[ersu]{0,4}s[.]?\s{0,}', re.IGNORECASE)

        for index, line in enumerate(lines):
                if not court_name_found:
                        court_name_match = pattern_court_name.search(line)
                        if court_name_match is not None:
                                court_name_found = 1
                                case = addCourtName(case,court_name_match.group(2).title())
                if not versus_found:                
                        versus_match = pattern_versus.search(line)
                        if versus_match is not None and index < 15:#it could match other versi in the text
                                versus_found = 1
                                petitioner = getPetitioner(index, lines)
                                XMLTree = addPetitioner(XMLTree,petitioner['party_name'], petitioner['petitioner_type'])
                                respondents_list,counsel_found_at = getRespondents(index, lines)
                                for respondent in respondents_list:
                                        XMLTree = addRespondent(XMLTree,respondent['party_name'], respondent['respondent_type'])
                if counsel_found_at != 0 and index == counsel_found_at:
                        counsel_group = getCounselGroup(index,lines)
                        XMLTree = addCounselGroup(XMLTree,counsel_group)
                        
                coram_match = pattern_coram.search(line)
                if coram_match is not None:
                        #print line
                        judge = coram_match.group(1)
                        position = coram_match.group(2)
                        #print position
                        coram_found=1
                        coram_found_at = index
                        #print line, index
                        case = addCoram(case,judge.strip(),position.strip())
                        
                elif coram_found==1 and index == (coram_found_at+1):
                        if '&' in line:
                                coram_next_match = pattern_coram_next.search(line)
                                if coram_next_match is not None:
                                        coram_found_at = index
                                        judge = coram_next_match.group(1)
                                        position = coram_next_match.group(2)
                                        case = addCoram(case,judge.strip(),position.strip())
                                        
                if coram_found==1 and index == (coram_found_at + 1):
                        date = parse(line.split(":")[1])
                        case = addDate(case, calendar.month_name[date.month],date.day,date.year,"Reserved")
                        
                elif coram_found==1 and index == (coram_found_at + 2):
                        date = parse(line.split(":")[1])
                        case = addDate(case, calendar.month_name[date.month],date.day,date.year,"Pronounced")
                if coram_found==1 and index == (coram_found_at + 3):
                        XMLTree = addJudgmentGroup(XMLTree, index, lines)
                        
                
        #ET.dump(case)
        XMLTree.write("XMLOutput - "+arg[:arg.find(".pdf")]+".xml")
