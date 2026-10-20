import { useNavigate } from "react-router-dom";
import { useRecoilState } from "recoil";
import { navatom } from "../../recoil/atom";

export default function Navcomp() {
    const [index, setIndex]: any = useRecoilState(navatom);

    const css1 = " text-black cursor-pointer w-full justify-items-center duration-300 ease-linear ";
    const css2 = " w-full duration-300 ease-linear ";
    const css3 = "text-black cursor-pointer w-full justify-items-center duration-300 ease-linear rounded-tr-lg";
    const css4 = "text-black cursor-pointer w-full justify-items-center duration-300 ease-linear rounded-br-lg";

    function getcss(i: number) {
        if (index === i) return css2;
        if (i == index - 1) return css3;
        if (i == index + 1) return css4;
        return css1;
    }

    return <div className="flex sm:flex-col w-full sm:w-fit pt-0 sm:pt-4 ">
        <NavItem css={getcss(0)} id={0} setIndex={setIndex} index={index} />
        <NavItem css={getcss(3)} id={3} setIndex={setIndex} index={index} url="home" text={"Home"} d={"m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"} />
        <NavItem css={getcss(1)} id={1} setIndex={setIndex} index={index} url="Transaction" text={"Transaction"} d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
        <NavItem css={getcss(4)} id={4} setIndex={setIndex} index={index} url="transfer" text={"Transfer"} d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
        <NavItem css={getcss(6)} id={6} setIndex={setIndex} index={index} />
    </div>
}

function NavItem(props: any) {
    if (props.id === 0 || props.id == 6) return <div className={props.css}></div>

    const nav = useNavigate();

    return <div className={props.css + " flex sm:pl-3 pt-1 pr-2 flex-col justify-center items-center sm:items-start sm:justify-normal sm:flex-row " + ((props.id === props.index)? "text-blue-700":" ") } onClick={() => { if (props.id != props.index) { props.setIndex(props.id); nav("/" + props.url) } }}>
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-max size-10 hover:scale-125 ease-in duration-300 ">
            <path strokeLinecap="round" strokeLinejoin="round" d={props.d} />
        </svg>
        <div className={ "visible w-max sm:pl-5 pt-1 sm:text-2xl"}>{props.text}</div>
    </div>
}