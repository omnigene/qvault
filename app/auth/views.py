from . import auth
from flask import json,request, redirect, render_template, url_for, flash, session
from flask_login import login_user
from sqlalchemy import or_
from ..models import User
from .forms import RegistrationForm, LoginForm
from ..import db
import random
from config import Config

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20190711 import sms_client, models
from tencentcloud.common.profile.client_profile import ClientProfile

from flask_mail import Message
from app import mail

@auth.route('/check', methods=['POST'])
def check_data():
    data=json.loads(request.get_data())
    if User.query.filter_by(**data).first():
        return 'false'
    else:
        return 'true'

def generate_code(len):
    code = ""
    for i in range(len):
        code += str(random.randint(0, 9))
    return code

@auth.route('/sms', methods=['POST'])
def send_sms():
    data=json.loads(request.get_data())
    mobile=data['mobile']
    receiver="+86"+mobile
    code = str('^%s$' % generate_code(6)) if data['code'] == '^$' else data['code']
    try:
        # 需注册腾讯云账户，获取账户密钥对SecretId和SecretKey
        cred = credential.Credential(Config.SMS_SECRET_ID, Config.SMS_SECRET_KEY)
        clientProfile = ClientProfile()
        client = sms_client.SmsClient(cred, "ap-guangzhou", clientProfile)
        req = models.SendSmsRequest()
        # 需在腾讯云中添加短信应用，生成短信API接口的SDKAppID
        req.SmsSdkAppid = "1400400789"
        req.Sign = "Qvault"
        req.PhoneNumberSet = [receiver]
        # 需在短信应用中设置并申请短信模板，获取短信模板ID（审核通过后才可用）
        req.TemplateID = "748406"
        req.TemplateParamSet = [code[1:-1]]
        resp = client.SendSms(req)
        verify_data={'mobile':mobile,'code':code,'msg':'注册验证码短信已发送。'}
        return verify_data, 200
    except TencentCloudSDKException as err:
        print('error', err)
        return "error", 400

@auth.route('/email', methods=['POST'])
def send_email():
    data=json.loads(request.get_data())
    code=str('^%s$'%generate_code(6)) if data['code']=='^$' else data['code']
    to=data['email']
    msg = Message('【Qvault】注册验证码', sender=Config.MAIL_USERNAME, recipients=[to])
    msg.html = render_template('auth/email_confirmation.html',code=code[1:-1])
    mail.send(msg)
    verify_data={'email':to,'code':code,'msg':'注册验证码邮件已发送。'}
    return verify_data, 200

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form=RegistrationForm()
    if request.method=='POST':
        user=User(username=form.username.data,
                  mobile=form.mobile.data or None,
                  email=form.email.data or None,
                  password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('您已注册成功！')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html',form=form)

@auth.route('/login-check', methods=['POST'])
def login_check():
    data=json.loads(request.get_data())
    account=data['account']
    user= User.query.filter(or_(User.username==account,User.mobile==account,User.email==account)).first()
    if user==None or not user.verify_password(data['input_password']):
        return 'false'
    return 'true'

@auth.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    account=form.account.data
    if request.method=='POST':
        user=User.query.filter(or_(User.username==account,User.mobile==account,User.email==account)).first()
        login_user(user,form.remember_me.data)
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)