from flask import Flask,request,redirect,url_for,render_template,flash,session,send_file,make_response
from flask_session import Session
from otp import genotp
from cmail import send_mail
from stoken import endata,dndata
from mysql.connector import (connection)
from io import BytesIO
import flask_excel as excel
import re
mydb=connection.MySQLConnection(user='root',host='localhost',password='admin',db='snm')
app=Flask(__name__)
excel.init_excel(app) #initialize excel with app
app.secret_key=b'\x0e\xad'
app.config['SESSION_TYPE']='filesystem' #storage type
Session(app) #intigration
@app.route('/',methods=['GET'])
def home():
    return render_template('welcome.html')
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form.get('username','').strip()
        useremail=request.form.get('useremail','').strip()
        userpassword=request.form.get('userpassword','').strip()
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s',[useremail])
            email_count=cursor.fetchone()#(1,) or (0,)
            if email_count[0]==0:
                print(request.form)
                gotp=genotp() #fuctioncalling
                userdetails={'username':username,'useremail':useremail,'userpassword':userpassword,'serverotp':gotp}
                subject='User registration Authentication OTP'
                body=f'Use the given otp {gotp}'
                send_mail(to=useremail,body=body,subject=subject)
                flash('otp has been sent to given mail')
                return redirect(url_for('otpverify',serverdata=endata(userdetails)))
            elif email_count[0]==1:
                flash('email already existed')
                return redirect(url_for('register'))
        except Exception as e:
            print(e)
            flash('Could not verify email')
            return redirect(url_for('register'))
    return render_template('register.html')
@app.route('/otp-verify/<serverdata>',methods=['GET','POST'])
def otpverify(serverdata):
    if request.method=='POST':
        userotp=request.form.get('otp')
        try:
            decrypteddata=dndata(serverdata) #dict data {'username':username,'useremail':useremail,'userpassword':userpassword,'serverotp':gotp}
        except Exception as e:
            print(e)
            flash('could not verify otp time out')
            return redirect(url_for('otpverify',serverdata=serverdata))
        if userotp==decrypteddata['serverotp']:
            try:
                cursor=mydb.cursor()
                cursor.execute('insert into userdata(user_name,useremail,password) values(%s,%s,%s)',[decrypteddata['username'],decrypteddata['useremail'],decrypteddata['userpassword']])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('cloudnot save db details')
                return redirect(url_for('otpverify',serverdata=serverdata))
            else:
                flash('User registration successfull')
                return redirect(url_for('otpverify',serverdata=serverdata))
        else:
            flash('Invalid OTP')
            return redirect(url_for('otpverify',serverdata=serverdata))
    return render_template('otpverify.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        login_email=request.form.get('useremail','').strip()
        login_password=request.form.get('userpassword')
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from userdata where useremail=%s',[login_email])
            email_count=cursor.fetchone()
            if email_count[0]==1:
                cursor.execute('select password from userdata where useremail=%s',[login_email])
                stored_password=cursor.fetchone()[0]
                if stored_password==login_password:
                    #create session info to identify user

                    session['userid']=login_email
                    return redirect(url_for('dashboard'))
                else:
                    flash('invalid password')
            elif email_count==0:
                flash('Email not found')
                return redirect(url_for('login'))
        except Exception as e:
                print(e)
                flash('cloud not verify login details')
                return redirect(url_for('login'))
    return render_template('login.html')
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if not session.get('userid'):
        flash ('pls login first')
        return redirect(url_for('login'))
    return render_template('dashboard.html')
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if not session.get('userid'):
        flash ('pls login first')
        return redirect(url_for('login'))
    if request.method=='POST':
        title=request.form.get('title','').strip()
        description=request.form.get('description','').strip()
        try :
            cursor=mydb.cursor(buffered= True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
            userid=cursor.fetchone()[0]
            cursor.execute('insert into notesdata(title,description,addedby) values(%s,%s,%s)',[title,description,userid])
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            flash('could not add notes')
            return redirect(url_for('addnotes'))
        else:
            flash('notes added successfully')
            return redirect(url_for('addnotes'))
    return render_template('addnotes.html')
@app.route('/viewallnotes',methods=['GET'])
def viewallnotes():
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select notesid,title,created_at from notesdata where addedby=%s',[userid])
        allnotes_data=cursor.fetchall()
        print(allnotes_data)
        return render_template('viewallnotes.html',allnotes_data=allnotes_data)
    except Exception as e :
        print(e)
        flash('could not fetch notes data')
        return redirect(url_for('dashboard'))
@app.route('/viewnotes/<notesid>',methods=['GET'])
def viewnotes(notesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select notesid,title,description,created_at from notesdata where addedby=%s and notesid=%s',[userid,notesid])
        notes_data=cursor.fetchone()
        print(notes_data)
        return render_template('viewnotes.html',notes_data=notes_data)
    except Exception as e :
        print(e)
        flash('could not fetch notes data')
        return redirect(url_for('viewallnotes'))
@app.route('/delete/<notesid>',methods=['GET'])
def delete(notesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('delete from notesdata where addedby=%s and notesid=%s',[userid,notesid])
        mydb.commit()
        flash('Notes deleted successfully')
        return redirect(url_for('viewallnotes'))
    except Exception as e :
        print(e)
        flash('could not delete notes')
        return redirect(url_for('viewallnotes'))
@app.route('/updatenotes/<notesid>',methods=['GET','POSt'])
def updatenotes(notesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select notesid,title,description,created_at from notesdata where addedby=%s and notesid=%s',[userid,notesid])
        notesdata=cursor.fetchone()
        print(notesdata)
        if request.method=='POST':
            print(request.form)
            updated_title=request.form.get('title')
            updated_description=request.form.get('description')
            cursor.execute('update notesdata set title=%s,description=%s where notesid=%s and addedby=%s',[updated_title,updated_description,notesid,userid])
            mydb.commit()
            cursor.close()
            flash('Notes updated successfully')
            return redirect(url_for('viewnotes',notesid=notesid))
        return render_template('updatenotes.html',notesdata=notesdata)
    except Exception as e :
        print(e)
        flash('could not fetch notes data')
        return redirect(url_for('viewallnotes'))
@app.route('/uploadfile',methods=['GET','POST'])
def uploadfile():
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    if request.method=='POST':
        filedata=request.files.get('file')
        fdata=filedata.read()
        fname=filedata.filename
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
            userid=cursor.fetchone()[0]
            cursor.execute('insert into filesdata(filename,filedata,addedby) values(%s,%s,%s)',[fname,fdata,userid])
            mydb.commit()
            cursor.close()
        except Exception as e:
            print(e)
            flash('Couldnot upload file')
            return redirect(url_for('uploadfile'))
        else:
            flash('File uploaded successfully')
            return redirect(url_for('uploadfile'))
    return render_template('uploadfile.html')
@app.route('/viewallfiles',methods=['GET'])
def viewallfiles():
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select filesid,filename,created_at from filesdata where addedby=%s',[userid])
        allfiles_data=cursor.fetchall()
        print(allfiles_data)
        return render_template('viewallfiles.html',allfiles_data=allfiles_data)
    except Exception as e :
        print(e)
        flash('could not fetch file data')
        return redirect(url_for('dashboard'))
@app.route('/deletefiles/<filesid>',methods=['GET'])
def deletefiles(filesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('delete from filesdata where addedby=%s and filesid=%s',[userid,filesid])
        mydb.commit()
        flash('File deleted successfully')
        return redirect(url_for('viewallfiles'))
    except Exception as e :
        print(e)
        flash('could not delete file')
        return redirect(url_for('viewallfiles'))
@app.route('/viewfile/<filesid>',methods=['GET','POST'])
def viewfile(filesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select filesid,filename,filedata,created_at from filesdata where addedby=%s and filesid=%s',[userid,filesid])
        file_details=cursor.fetchone()
        print(file_details[2])
        filedata=BytesIO(file_details[2])#reads binary stream data
        return send_file(filedata,as_attachment=False,download_name=f'{file_details[1]}')
    except Exception as e:
        print(e)
        flash('could not view file')
        return redirect(url_for('viewallfiles'))
@app.route('/downloadfile/<filesid>',methods=['GET','POST'])
def downloadfile(filesid):
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select filesid,filename,filedata,created_at from filesdata where addedby=%s and filesid=%s',[userid,filesid])
        file_detail=cursor.fetchone()
        print(file_detail[2])
        filedata=BytesIO(file_detail[2])#reads binary stream data
        return send_file(filedata,as_attachment=True,download_name=f'{file_detail[1]}')
    except Exception as e:
        print(e)
        flash('could not view file')
        return redirect(url_for('viewallfiles'))
@app.route('/getexceldata',methods=['GET','POST'])
def getexceldata():
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
        userid=cursor.fetchone()[0]
        cursor.execute('select notesid,title,description,created_at from notesdata where addedby=%s',[userid])
        allnotes_data=cursor.fetchall()
        print(allnotes_data)
        array_data=[list(i) for i in allnotes_data]
        heading=['Notesid','Title','Description','Created_at']
        array_data.insert(0,heading)
        return excel.make_response_from_array(array_data,'xlsx',file_name='notesexceldata')
    except Exception as e:
        print(e)
        flash('could not generate excel')
        return redirect(url_for(dashboard))
@app.route('/search',methods=['POST'])
def search():
    if not session.get('userid'):
        flash('pls login first')
        return redirect(url_for('login'))
    try:
        searchdata=request.form['sdata']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        if pattern.match(searchdata):
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from userdata where useremail=%s',[session.get('userid')])
            userid=cursor.fetchone()[0]
            cursor.execute('select notesid,title,created_at from notesdata where addedby=%s  and (notesid like %s or title like %s or description like %s or created_at like %s)',[userid,searchdata+'%',searchdata+'%',searchdata+'%',searchdata+'%'])
            searchresult=cursor.fetchall()
            return render_template('searchresult.html',searchresult=searchresult)
        else:
            flash('invalid searchdata')
            return redirect(url_for('dashboard'))
    except Exception as e:
        print(e)
        flash('could not fetch searchdata')
        return redirect(url_for('dashboard'))
@app.route('/logout')
def logout():
    if not request.cookies.get('UserId'):
        return redirect(url_for('login'))
    resp=make_response(redirect(url_for('login')))
    resp.delete_cookie('UserId')
    return resp   
if __name__=='__main__':
    app.run(debug=True,use_reloader=True)