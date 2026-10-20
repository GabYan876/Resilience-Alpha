import {atom} from 'recoil';
import { loadSession } from '../session';

const session = loadSession();


export const logined = atom({
    key:"logined",
    default:session.token !== null
})

export const baseurl = atom({
    key:"baseurl",
    default:""
})

export const navatom = atom({
    key:"navatom",
    default:3
})

export const userinfo = atom({
    key:"userinfo",
    default:session.user
})

export const payment = atom({
    key:"payment",
    default:{}
})

export const request = atom({
    key:"request",
    default:[]
})