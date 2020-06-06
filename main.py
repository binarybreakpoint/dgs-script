#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pdfquery
import requests
from datetime import datetime, timedelta
from lxml import html
import copy as copy


# In[2]:


template = pdfquery.PDFQuery("./template.pdf")
template.load()

pdf = pdfquery.PDFQuery("./example.pdf")
pdf.load()


# In[3]:


# Obter bounding boxes a partir do pdf 'template' #
def enlargeBbox(bbox):
    res = [x for x in bbox]
    res[0]-=20
    res[1]-=2
    res[2]+=20
    res[3]+=2
    res = ",".join([str(x) for x in res])
    #"x0,y0,x1,y1"
    return res

#valores do pdf 'template'
#usados para obter as bounding boxes dos valores
attrs = {
    "norte": "16834",
    "norte_o": "803",
    "centro": "3789",
    "centro_o": "244",
    "LVT": "12473",
    "LVT_o": "387",
    "alentejo": "263",
    "alentejo_o": "1",
    "algarve": "380",
    "algarve_o": "15",
    "açores": "140",
    "açores_o": "15",
    "madeira": "90",
    "madeira_o": "0",

    "suspeitos": "334923",
    "confirmados": "33969",
    "nao_confirmados": "299318",
    "aguardam": "1636",
    "recuperados": "20526",
    "obitos": "1465",
    "contactos": "28088",
    #casos especiais, 4ª pagina
    "UCI": "58",
    "internados": "421"
}


bboxes = {
    
}

res = {
    
}

def select_match(objs,query):
    #filtrar None's
    matches = list(filter(lambda x: not x.text is None,objs))
    #seleccionar primeiro elemento com texto correto
    matches = list(filter(lambda x: x.text.strip()==str(query), matches)) 
    return matches[0]

for attr in attrs.keys():
    #obter bboxes
    val = attrs[attr]
    matchObj = select_match(template.pq(f"*:contains('{val}')"),val)
    bbox = enlargeBbox(matchObj.layout.bbox)
    bboxes[attr] = bbox


# In[4]:


# Obter dados dado um pdf #

def get_values(pdf):
    extract_query = [('with_parent','LTPage[page_index="0"]')]
    #adicionar query por bounding box por cada atributo
    for attr in bboxes.keys():
        if(attr!="UCI" and attr!="internados"):
            extract_query.append( (attr, f":in_bbox('{bboxes[attr]}')") )
    
    extract_query.append( ('with_parent','LTPage[page_index="3"]') )
    extract_query.append( ('UCI', f":in_bbox('{bboxes['UCI']}')") )
    extract_query.append( ('internados', f":in_bbox('{bboxes['internados']}')") )
    
    #extrair matches
    res = pdf.extract(extract_query)
    for key in res.keys():
        res[key].sort(key=len)
        if(len(res[key])):
            res[key] = int(res[key][0].text.strip())
    return res


# In[5]:


#output de um pdf exemplo
display(get_values(pdf))


# In[6]:


#Obter dados da página do Min.Saúde
page = requests.get('https://covid19.min-saude.pt/relatorio-de-situacao/')
tree = html.fromstring(page.content)

todayStr = datetime.today().strftime('%d/%m/%Y')
yesterdayStr = datetime.strftime(datetime.now() - timedelta(1), '%d/%m/%Y')


# In[7]:


tree = html.fromstring(page.content)
today_link = tree.xpath(f"//a[contains(text(), '{todayStr}')]")
all_links = tree.xpath("//*[@class='single_content']/ul/li/a")

#Se não tem dados de hoje
if(not len(today_link)):
    print("Getting yesterday's stats")
    todayStr = yesterdayStr

#Obtém últimos 6 pdf's
pdf_links = [x.attrib['href'] for x in all_links[:6]]
for (i,link) in enumerate(pdf_links):

    r = requests.get(link, stream=True)

    with open(f"./latest/{i}.pdf", 'wb') as fd:
        for chunk in r.iter_content(2048):
            fd.write(chunk)

    print("downloading ",link)

#Obtém dados dos pdfs
print("Parsing pdf's...")
pdfs = [pdfquery.PDFQuery(f"./latest/{x}.pdf") for x in range(6)]
print("Getting values...")
vals = [get_values(x) for x in pdfs]


# In[8]:


#Agrupa dados dos últimos dias numa lista
_attrs = copy.copy(vals[0])

for k in _attrs.keys():
    _attrs[k] = []

for file_vals in vals:
    for attr in file_vals:
        _attrs[attr].append(file_vals[attr])
        
display(_attrs)


# In[9]:


#Cálcula casos ativos
_attrs['ativos'] = []
for i in range(6):
    _attrs['ativos'].append( _attrs['confirmados'][i] - _attrs['recuperados'][i] - _attrs['obitos'][i])
print(_attrs['ativos'])


# In[19]:


#pretty print dos valores
def diff_str(val,end=""):
    if(end=="%"):
        val_str = str(round(val,2))
    else:
        val_str = str(val)
    if(val >=0):
        return f"+{val_str}{end}"
    else:
        return f"{val_str}{end}"

def latest(k):
    return str(_attrs[k][0])
def var(k):
    return diff_str(_attrs[k][0] - _attrs[k][1])
def var_d(k,days=1):
    if(_attrs[k][0+days] == 0):
        return "--"
    diff = _attrs[k][0] - _attrs[k][0+days]
    diff_p = diff*100/_attrs[k][0+days]
    return diff_str(diff_p,end="%")


def row_str(attr):
    return f"|{latest(attr)}|{var(attr)}|{var_d(attr,1)}|{var_d(attr,3)}|{var_d(attr,5)}|"
    

def aumento():
    novos = int(var('confirmados'))
    ativos = int(latest('ativos'))
    diff_p = novos*100/ativos
    return diff_str(diff_p,end="%")

template_txt = f"""

# ATUALIZAÇÃO DIÁRIA - {todayStr}

---

|👥 Totais|Variação|📈 1 dia|📈 3 dias|📈 5 dias|
:--|:--|:--|:--|:--|
{row_str('confirmados')}
|**✔️ Recuperados**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
{row_str('recuperados')}
|**☠️ Óbitos**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
{row_str('obitos')}
|**🏥 Internados**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
{row_str('internados')}
|🛌 **UCI**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
{row_str('UCI')}
|😷 **Ativos**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
{row_str('ativos')}

---

|📊 **Aumento de Novos Casos face a Casos Ativos:**|
:--|
| {aumento()}|

---

## Por região

**Casos Confirmados**

|Região|👥 Totais|Variação|📈 1 dia|📈 3 dias|📈 5 dias|
:--|:--|:--|:--|:--|:--|
|**Norte**{row_str('norte')}
|**Centro**{row_str('centro')}
|**LVT**{row_str('LVT')}
|**Alentejo**{row_str('alentejo')}
|**Algarve**{row_str('algarve')}
|**Açores**{row_str('açores')}
|**Madeira**{row_str('madeira')}

**Óbitos**

|Região|**☠️ Óbitos**|**Variação**|**📈 1 dia**|**📈 3 dias**|**📈 5 dias**|
:--|:--|:--|:--|:--|:--|
|**Norte**{row_str('norte_o')}
|**Centro**{row_str('centro_o')}
|**LVT**{row_str('LVT_o')}
|**Alentejo**{row_str('alentejo_o')}
|**Algarve**{row_str('algarve_o')}
|**Açores**{row_str('açores_o')}
|**Madeira**{row_str('madeira_o')}

---

**Dados obtidos automaticamente do site da DGS**

[Código fonte disponível aqui](https://github.com/binarybreakpoint/dgs-script)
"""


print(template_txt)


# In[ ]:




