# coding=utf-8
from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_qrcode import QRcode
import os
from datetime import datetime
#from werkzeug import secure_filename
from fpdf import FPDF
import PyPDF2
from PyPDF2.generic import BooleanObject, NameObject, IndirectObject, NumberObject, TextStringObject
import requests
import subprocess

app = Flask(__name__)
qrcode = QRcode(app)


app.config["DOCS_UPLOADS"] = "uploads"
app.config["ALLOWED_DOCS_EXTENSIONS"] = ["PDF"]


def set_need_appearances_writer(writer):
    # basically used to ensured there are not 
    # overlapping form fields, which makes printing hard
    try:
        catalog = writer._root_object
        # get the AcroForm tree and add "/NeedAppearances attribute
        if "/AcroForm" not in catalog:
            writer._root_object.update({
                NameObject("/AcroForm"): IndirectObject(len(writer._objects), 0, writer)})

        need_appearances = NameObject("/NeedAppearances")
        writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)


    except Exception as e:
        print('set_need_appearances_writer() catch : ', repr(e))

    return writer

def pdf_flatten(filename, number):
    # open the pdf
    input_stream = open(filename, "rb")
    pdf_reader = PyPDF2.PdfFileReader(input_stream, strict=False)
    if "/AcroForm" in pdf_reader.trailer["/Root"]:
        pdf_reader.trailer["/Root"]["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)})

    pdf_writer = PyPDF2.PdfFileWriter()
    set_need_appearances_writer(pdf_writer)
    if "/AcroForm" in pdf_writer._root_object:
        # Acro form is form field, set needs appearances to fix printing issues
        pdf_writer._root_object["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)})

    data_dict = pdf_reader.getFields() # this is a dict of your DB form values

    flatten_dict = ("number")

    for thisPage in range (pdf_reader.numPages):
        pdf_writer.addPage(pdf_reader.getPage(thisPage))
        page = pdf_writer.getPage(thisPage)
        for j in range(0, len(page['/Annots'])):
            writer_annot = page['/Annots'][j].getObject()
            for field in data_dict:
                if writer_annot.get('/T') == field:
                    if field in flatten_dict:
                        writer_annot.update({
                            NameObject("/Ff"): NumberObject(1)    # make ReadOnly
                            , NameObject("/V"): TextStringObject(number)    # update the value
                        })

    flatten_form = filename+"-flatten.pdf"
    output_stream = open(flatten_form, "wb")
    pdf_writer.write(output_stream)
    return flatten_form

def add_qrcode(filename, number):
    form_name = os.path.join(app.config["DOCS_UPLOADS"], filename)
    f = PyPDF2.PdfFileReader(form_name)
    ff = f.getFields()
    doctype = ff["doctype"]['/DV']
    qrdata = doctype+"|"+number
    url = 'http://localhost:3000/qrcode?data='+qrdata

    image_path = os.path.join(app.config["DOCS_UPLOADS"], 'qrcode'+datetime.now().strftime("%Y%m%d%H%M%S%f")+'.png')

    response = requests.get(url)

    file = open(image_path, "wb")
    file.write(response.content)
    file.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.image(image_path, x=180, y=15, w=15)
    add_qrcode = os.path.join(app.config["DOCS_UPLOADS"], 'add_qrcode'+datetime.now().strftime("%Y%m%d%H%M%S%f")+'.pdf')
    pdf.add_page()
    pdf.output(add_qrcode)

    stamp_form = form_name+'-stamp.pdf'
    return_code = subprocess.call("pdftk "+form_name+" multistamp "+add_qrcode+" output "+stamp_form, shell=True)

    flatten_form = pdf_flatten(stamp_form, number)
    return flatten_form




def allowed_docs(filename):
    if not "." in filename:
        return False
    ext = filename.rsplit(".", 1)[1]
    if ext.upper() in app.config["ALLOWED_DOCS_EXTENSIONS"]:
        return True
    else:
        return False

@app.route('/upload')
def upload_file():
    return render_template('upload.html')

@app.route("/qrform", methods=["GET", "POST"])
def upload_docs():
    if request.method == "POST":
        if request.files:
            docs = request.files["docs"]
            if docs.filename == "":
                print("No filename")
                return redirect(request.url)
            if allowed_docs(docs.filename):
                #filename = secure_filename(docs.filename)
                filename = datetime.now().strftime("%Y%m%d%H%M%S%f")
                docs.save(os.path.join(app.config["DOCS_UPLOADS"], filename))
                number = request.form["number"]
                stamp_form = add_qrcode(filename, number)
                return send_file(stamp_form)
            else:
                print("That file extension is not allowed")
                return redirect(request.url)
    return render_template("upload.html")

@app.route("/")
def index():
    return render_template("qrapi.html")


@app.route("/qrcode", methods=["GET"])
def get_qrcode():
    # please get /qrcode?data=<qrcode_data>
    data = request.args.get("data", "")
    return send_file(qrcode(data, mode="raw"), mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
