import { useRecoilValue, useSetRecoilState } from "recoil";
import { baseurl, logined, userinfo } from "../../recoil/atom";
import { Outlet, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import axios from "axios";
import { clearSession } from "../../session";

export default function Auth() {
    const login: boolean = useRecoilValue(logined);
    const setLogined = useSetRecoilState(logined);
    const setUser = useSetRecoilState(userinfo);
    const url = useRecoilValue(baseurl);

    const navigate = useNavigate();

    useEffect(() => {
        if (!login) navigate("/");
    }, [login, navigate]);

    // Après un rafraîchissement, le profil vient du navigateur : on relit le solde auprès du
    // back et on déconnecte si le jeton a expiré.
    useEffect(() => {
        if (!login) return;
        const token = sessionStorage.getItem("token");
        axios.get(url + "/me/account", { headers: { Authorization: "Bearer " + token } })
            .then((res) => {
                setUser((u) => ({ ...u, uid: res.data.iban_fake, balance: res.data.balance_cents }));
            }).catch((err) => {
                if (err.response?.status === 401) {
                    clearSession();
                    setLogined(false);
                }
            });
    }, [login, url, setUser, setLogined]);

    return (login) ? <Outlet /> : <div></div>;
}
