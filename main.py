#!/usr/bin/env python3
# SatTracker V1.1 - Doppler + Transponder + TX offset + IC-705 + Maasbree WebSDR
# WebSDR read-only; operator tunes WebSDR manually; WebSDR starts automatically.

import threading
import tkinter as tk
import configparser
from tkinter import ttk,messagebox
from zoneinfo import ZoneInfo
from websdr import WebSDR

try:
    from skyfield.api import EarthSatellite,load,wgs84
except ImportError:
    raise SystemExit("Skyfield missing.\n\nInstall with:\npip install skyfield")

try:
    from ic705 import IC705
except ImportError:
    IC705=None

class SatTracker:
    @staticmethod
    def load_config(filename="sattracker.ini"):
        config=configparser.ConfigParser()
        if not config.read(filename):
            raise SystemExit(f"Configuration file not found:\n\n{filename}")
        if "settings" not in config:
            raise SystemExit(f"Section [settings] missing in:\n\n{filename}")
        settings=config["settings"]
        satellites={}
        for section in config.sections():
            if section.startswith("satellite_"):
                name=section[10:]
                s=config[section]
                satellites[name]={
                    "norad":s.getint("norad"),
                    "tle_name":s.get("tle_name"),
                    "uplink_min":s.getfloat("uplink_min")*1e6,
                    "uplink_max":s.getfloat("uplink_max")*1e6,
                    "downlink_min":s.getfloat("downlink_min")*1e6,
                    "downlink_max":s.getfloat("downlink_max")*1e6,
                    "center_tx":s.getfloat("center_tx")*1e6,
                    "center_rx":s.getfloat("center_rx")*1e6,
                    "tx_offset":s.getint("tx_offset"),
                    "tx_mode":s.get("tx_mode"),
                    "rx_mode":s.get("rx_mode"),
                    "fm":s.getboolean("fm")
                }
        if not satellites:
            raise SystemExit(f"No satellites found in:\n\n{filename}")
        return config,satellites

    def __init__(self,root):
        self.config,self.satellites=self.load_config()
        settings=self.config["settings"]
        self.tle_url=settings.get("tle_url","https://www.amsat.org/tle/current/dailytle.txt")
        self.local_tz=ZoneInfo(settings.get("timezone","Europe/Amsterdam"))
        self.update_ms=settings.getint("update_ms",1000)
        self.pass_search_days=settings.getfloat("pass_search_days",2.0)
        self.ic705_port=settings.get("ic705_port","")
        self.ic705_baudrate=settings.getint("ic705_baudrate",19200)
        self.tx_offset_step=settings.getint("tx_offset_step",100)
        self.default_tx_offset=settings.getint("default_tx_offset",-2400)
        self.speed_of_light=settings.getfloat("speed_of_light",299792.458)
        self.locator_default=settings.get("locator","JO32AM")
        self.height_default=settings.getfloat("height",8)
        self.websdr_url=settings.get("websdr_url","")

        if "tracker" in self.config:
            tracker=self.config["tracker"]
            self.default_satellite=tracker.get("default_satellite",list(self.satellites.keys())[0])
        else:
            self.default_satellite=list(self.satellites.keys())[0]
        if self.default_satellite not in self.satellites:
            self.default_satellite=list(self.satellites.keys())[0]

        self.root=root
        self.root.title("Satellite Tracker V1.1")
        self.root.geometry("820x520")
        self.root.minsize(740,520)
        self.ts=load.timescale()
        self.sat=None
        self.observer=None
        self.running=True

        self.locator=tk.StringVar(value=self.locator_default)
        self.altitude=tk.DoubleVar(value=self.height_default)
        self.satellite_name=tk.StringVar(value=self.default_satellite)
        self.sat_config=self.satellites[self.default_satellite]
        self.mode=tk.StringVar(value="FM" if self.sat_config["fm"] else self.sat_config["tx_mode"])
        self.tx_offset=tk.IntVar(value=self.sat_config.get("tx_offset",self.default_tx_offset))
        self.websdr_rx_frequency=None
        self.status=tk.StringVar(value="TLE loading...")
        self.az=tk.StringVar(value="---°")
        self.el=tk.StringVar(value="---°")
        self.range_km=tk.StringVar(value="--- km")
        self.rx=tk.StringVar(value="--- MHz")
        self.tx=tk.StringVar(value="--- MHz")
        self.actual_rx=tk.StringVar(value="--- MHz")
        self.actual_tx=tk.StringVar(value="--- MHz")
        self.doppler_rx=tk.StringVar(value="--- Hz")
        self.doppler_tx=tk.StringVar(value="--- Hz")
        self.aos=tk.StringVar(value="--:--:--")
        self.los=tk.StringVar(value="--:--:--")
        self.countdown=tk.StringVar(value="---")
        self.current_aos=None
        self.current_los=None

        self.ic705=None
        if IC705:
            try:
                self.ic705=IC705(self.ic705_port,self.ic705_baudrate)
                print(f"IC-705 connected via {self.ic705_port}")
            except Exception as e:
                print(f"IC-705 not connected: {e}")

        self.websdr=None
        self.websdr_on=False
        self.build_ui()
        self.update_qth()
        self.load_tle()
        self.root.after(500,self.start_websdr)
        self.root.after(self.update_ms,self.update_display)

    def select_satellite(self,event=None):
        name=self.satellite_name.get()
        if name not in self.satellites:return
        self.sat_config=self.satellites[name]
        self.tx_offset.set(self.sat_config.get("tx_offset",self.default_tx_offset))
        self.mode.set("FM" if self.sat_config["fm"] else self.sat_config["tx_mode"])
        print(f"\n======================================\nSATELLITE SELECTED: {name}\nTX OFFSET: {self.tx_offset.get():+d} Hz\n======================================")
        self.websdr_rx_frequency=None
        self.current_aos=None
        self.current_los=None
        self.aos.set("--:--:--")
        self.los.set("--:--:--")
        self.countdown.set("---")
        self.rx.set("--- MHz")
        self.tx.set("--- MHz")
        self.actual_rx.set("--- MHz")
        self.actual_tx.set("--- MHz")
        self.doppler_rx.set("--- Hz")
        self.doppler_tx.set("--- Hz")
        self.status.set(f"{name} selected — TLE loading...")
        self.update_mode_values()
        self.update_mode_combo()
        self.update_footer()
        self.load_tle()

    def update_mode_values(self,event=None):
        mode=self.mode.get()
        if self.sat_config["fm"]:
            mode="FM"
            self.mode.set(mode)
        if self.ic705:
            try:
                self.ic705.set_mode(mode)
                print(f"IC-705 TX mode = {mode}")
            except Exception as e:
                print(f"IC-705 mode error: {e}")

    def build_ui(self):
        root=self.root
        root.configure(bg="#101010")
        tk.Label(root,text="SATELLITE TRACKER",font=("DejaVu Sans",28,"bold"),fg="white",bg="#101010").pack(pady=(10,2))
        tk.Label(root,textvariable=self.status,font=("DejaVu Sans",12,"bold"),fg="#dddddd",bg="#101010").pack()

        freq=tk.Frame(root,bg="#101010")
        freq.pack(fill="x",padx=27,pady=12)
        self.make_freq_block(freq,"WEBSDR RX",self.rx,0,bg="#26384a")
        self.make_freq_block(freq,"IC-705 TX",self.tx,1,bg="#26384a")

        input_frame=tk.Frame(root,bg="#4a2020",bd=1,relief="solid")
        input_frame.pack(fill="x",padx=35,pady=(0,12))
        tk.Label(input_frame,text="TX OFFSET (Hz)",font=("DejaVu Sans",11,"bold"),fg="#aaaaaa",bg="#4a2020").pack(pady=(8,4))
        entry_frame=tk.Frame(input_frame,bg="#4a2020")
        entry_frame.pack(pady=(0,10))
        tk.Button(entry_frame,text="−",width=3,command=lambda:self.change_tx_offset(-self.tx_offset_step)).pack(side="left",padx=2)
        tk.Label(entry_frame,textvariable=self.tx_offset,width=7,font=("DejaVu Sans",12,"bold"),fg="white",bg="#4a2020").pack(side="left",padx=2)
        tk.Button(entry_frame,text="+",width=3,command=lambda:self.change_tx_offset(self.tx_offset_step)).pack(side="left",padx=2)

        info=tk.Frame(root,bg="#101010")
        info.pack(fill="x",padx=30)
        labels=[("AZIMUTH",self.az),("ELEVATION",self.el),("RANGE",self.range_km),("COUNTDOWN",self.countdown)]
        for i,(name,var) in enumerate(labels):
            box=tk.Frame(info,bg="#1c1c1c",bd=1,relief="solid")
            box.grid(row=0,column=i,padx=4,pady=4,sticky="nsew")
            info.columnconfigure(i,weight=1)
            tk.Label(box,text=name,font=("DejaVu Sans",9,"bold"),fg="#aaaaaa",bg="#1c1c1c").pack(pady=(7,2))
            tk.Label(box,textvariable=var,font=("DejaVu Sans",15,"bold"),fg="white",bg="#1c1c1c").pack(pady=(0,7))

        combined=tk.Frame(root,bg="#101010")
        combined.pack(fill="x",padx=35,pady=10)
        for i in range(4):combined.columnconfigure(i,weight=1)

        pass_frame=tk.Frame(combined,bg="#1c1c1c",bd=1,relief="solid")
        pass_frame.grid(row=0,column=0,padx=(0,5),sticky="nsew")
        pass_frame.columnconfigure(0,weight=1)
        pass_frame.columnconfigure(1,weight=1)
        tk.Label(pass_frame,text="PASS",font=("DejaVu Sans",11,"bold"),fg="#aaaaaa",bg="#1c1c1c").grid(row=0,column=0,columnspan=2,pady=(8,5))
        for row,name,var in [(1,"AOS",self.aos),(2,"LOS",self.los)]:
            pady=4 if row==1 else (4,10)
            tk.Label(pass_frame,text=name,font=("DejaVu Sans",11,"bold"),fg="white",bg="#1c1c1c").grid(row=row,column=0,padx=15,pady=pady,sticky="e")
            tk.Label(pass_frame,textvariable=var,font=("DejaVu Sans",14,"bold"),fg="white",bg="#1c1c1c").grid(row=row,column=1,padx=15,pady=pady,sticky="w")

        dop=tk.Frame(combined,bg="#1c1c1c",bd=1,relief="solid")
        dop.grid(row=0,column=1,padx=5,sticky="nsew")
        dop.columnconfigure(0,weight=1)
        dop.columnconfigure(1,weight=1)
        tk.Label(dop,text="DOPPLER",font=("DejaVu Sans",11,"bold"),fg="#aaaaaa",bg="#1c1c1c").grid(row=0,column=0,columnspan=2,pady=(8,5))
        for row,name,var in [(1,"RX 435 MHz",self.doppler_rx),(2,"TX 145 MHz",self.doppler_tx)]:
            pady=4 if row==1 else (4,10)
            tk.Label(dop,text=name,font=("DejaVu Sans",11),fg="white",bg="#1c1c1c").grid(row=row,column=0,padx=15,pady=pady,sticky="e")
            tk.Label(dop,textvariable=var,font=("DejaVu Sans",12,"bold"),fg="white",bg="#1c1c1c").grid(row=row,column=1,padx=15,pady=pady,sticky="w")

        sat_frame=tk.Frame(combined,bg="#1c1c1c",bd=1,relief="solid")
        sat_frame.grid(row=0,column=2,padx=5,sticky="nsew")
        tk.Label(sat_frame,text="SATELLITE",font=("DejaVu Sans",11,"bold"),fg="#aaaaaa",bg="#1c1c1c").pack(pady=(8,5))
        self.satellite_combo=ttk.Combobox(sat_frame,textvariable=self.satellite_name,values=list(self.satellites.keys()),state="readonly",width=12,justify="center",font=("DejaVu Sans",14,"bold"))
        self.satellite_combo.pack(padx=10,pady=(3,14))
        self.satellite_combo.bind("<<ComboboxSelected>>",self.select_satellite)

        mode_frame=tk.Frame(combined,bg="#1c1c1c",bd=1,relief="solid")
        mode_frame.grid(row=0,column=3,padx=(5,0),sticky="nsew")
        tk.Label(mode_frame,text="TX MODE",font=("DejaVu Sans",11,"bold"),fg="#aaaaaa",bg="#1c1c1c").pack(pady=(8,5))
        self.mode_combo=ttk.Combobox(mode_frame,textvariable=self.mode,values=["LSB","CW","RTTY"],state="readonly",width=8,justify="center",font=("DejaVu Sans",14,"bold"))
        self.mode_combo.pack(padx=10,pady=(3,14))
        self.mode_combo.bind("<<ComboboxSelected>>",self.update_mode_values)
        self.update_mode_combo()

        self.footer=tk.Label(root,text="",font=("DejaVu Sans",8),fg="#777777",bg="#101010")
        self.footer.pack(side="bottom",pady=7)
        self.update_footer()

    def update_mode_combo(self):
        if self.sat_config["fm"]:
            self.mode_combo["values"]=["FM"]
            self.mode.set("FM")
            self.mode_combo.configure(state="disabled")
        else:
            self.mode_combo["values"]=["LSB","CW","RTTY"]
            self.mode_combo.configure(state="readonly")

    def make_freq_block(self,parent,name,variable,column,bg="#1c1c1c"):
        frame=tk.Frame(parent,bg=bg,bd=2,relief="solid")
        frame.grid(row=0,column=column,padx=7,sticky="nsew")
        parent.columnconfigure(column,weight=1)
        tk.Label(frame,text=name,font=("DejaVu Sans",12,"bold"),fg="#bbbbbb",bg=bg).pack(pady=(7,2))
        tk.Label(frame,textvariable=variable,font=("DejaVu Sans",20,"bold"),fg="white",bg=bg).pack(pady=(0,8))

    def websdr_frequency_callback(self,frequency):
        try:self.websdr_rx_frequency=float(frequency)
        except Exception:pass

    def start_websdr(self):
        if self.websdr_on:return
        print(f"\n======================================\nMAASBREE WEBSDR START\nURL: {self.websdr_url}\nWebSDR is tuned manually.\nSatTracker only reads the frequency.\nSatTracker sends nothing to the WebSDR.\n======================================")
        self.websdr_rx_frequency=None
        try:
            self.websdr=WebSDR(self.websdr_url,frequency_callback=self.websdr_frequency_callback)
            self.websdr_on=True
            self.websdr.start()
        except Exception as e:
            self.websdr_on=False
            self.websdr=None
            print(f"WebSDR start error: {e}")
            self.status.set(f"WebSDR error: {e}")

    def update_footer(self):
        cfg=self.sat_config
        self.footer.config(text=f"{self.satellite_name.get()} | {self.locator.get()} | {cfg['uplink_min']/1e6:.3f}–{cfg['uplink_max']/1e6:.3f} MHz UP | {cfg['downlink_min']/1e6:.3f}–{cfg['downlink_max']/1e6:.3f} MHz DOWN | {self.local_tz.key}")

    def maidenhead_to_latlon(self,locator):
        locator=locator.strip().upper()
        if len(locator) not in (4,6):raise ValueError("Maidenhead locator must be 4 or 6 characters.")
        if not ("A"<=locator[0]<="R" and "A"<=locator[1]<="R"):raise ValueError("Invalid Maidenhead locator.")
        if not (locator[2].isdigit() and locator[3].isdigit()):raise ValueError("Invalid Maidenhead locator.")
        lon=-180+(ord(locator[0])-ord("A"))*20
        lat=-90+(ord(locator[1])-ord("A"))*10
        lon+=int(locator[2])*2
        lat+=int(locator[3])
        if len(locator)==6:
            if not ("A"<=locator[4]<="X" and "A"<=locator[5]<="X"):raise ValueError("Invalid Maidenhead subsquare.")
            lon+=(ord(locator[4])-ord("A"))*(5/60)
            lat+=(ord(locator[5])-ord("A"))*(2.5/60)
            lon+=2.5/60
            lat+=1.25/60
        else:
            lon+=1.0
            lat+=0.5
        return lat,lon

    def update_qth(self):
        try:
            locator=self.locator.get().strip().upper()
            altitude=float(self.altitude.get())
            lat,lon=self.maidenhead_to_latlon(locator)
            self.observer=wgs84.latlon(lat,lon,elevation_m=altitude)
            self.locator.set(locator)
            self.status.set(f"QTH {locator}")
            self.update_footer()
        except ValueError as e:
            messagebox.showerror("Satellite Tracker",str(e))

    def load_tle(self):
        selected_name=self.satellite_name.get()
        cfg=self.satellites[selected_name]

        def worker():
            try:
                from urllib.request import Request,urlopen
                request=Request(self.tle_url,headers={"User-Agent":"Mozilla/5.0"})
                response=urlopen(request,timeout=15)
                text=response.read().decode("utf-8",errors="replace")
                lines=[line.strip() for line in text.splitlines() if line.strip()]
                line1=None
                line2=None
                name=selected_name
                norad_text=str(cfg["norad"])

                for i in range(len(lines)-1):
                    if lines[i].startswith("1 ") and norad_text in lines[i] and lines[i+1].startswith("2 "):
                        line1=lines[i]
                        line2=lines[i+1]
                        break

                if line1 is None:
                    for i in range(len(lines)-2):
                        if cfg["tle_name"].upper() in lines[i].upper() and lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
                            name=lines[i]
                            line1=lines[i+1]
                            line2=lines[i+2]
                            break

                if line1 is None or line2 is None:
                    raise RuntimeError(f"{selected_name} (NORAD {cfg['norad']}) not found.")

                satellite=EarthSatellite(line1,line2,name,self.ts)

                if self.satellite_name.get()==selected_name:
                    self.sat=satellite
                    self.root.after(0,lambda:self.status.set(f"TLE loaded — tracking {selected_name}"))
                    self.root.after(0,self.update_footer)

            except Exception as e:
                error=str(e)
                self.root.after(0,lambda:self.status.set(f"TLE error: {error}"))

        threading.Thread(target=worker,daemon=True).start()

    def get_range_rate(self,t):
        difference=self.sat-self.observer
        topocentric=difference.at(t)
        pos=topocentric.position.km
        vel=topocentric.velocity.km_per_s
        distance=(pos[0]**2+pos[1]**2+pos[2]**2)**0.5
        if distance==0:return 0.0,0.0
        radial_velocity=(pos[0]*vel[0]+pos[1]*vel[1]+pos[2]*vel[2])/distance
        return float(radial_velocity),float(distance)

    def calculate_tracking_frequencies(self,radial_velocity,heard_rx):
        beta=radial_velocity/self.speed_of_light
        cfg=self.sat_config
        radio_rx=heard_rx
        satellite_downlink=radio_rx/(1.0-beta)
        transponder_sum=cfg["center_tx"]+cfg["center_rx"]
        satellite_uplink=transponder_sum-satellite_downlink
        radio_tx=satellite_uplink/(1.0-beta)+self.tx_offset.get()
        rx_doppler=radio_rx-satellite_downlink
        tx_doppler=radio_tx-satellite_uplink
        return radio_rx,radio_tx,satellite_downlink,satellite_uplink,rx_doppler,tx_doppler

    def change_tx_offset(self,amount):
        self.tx_offset.set(self.tx_offset.get()+amount)
        print(f"TX offset = {self.tx_offset.get():+d} Hz")

    def find_pass_events(self):
        if not self.sat or not self.observer:return []
        now=self.ts.now()
        start=self.ts.tt_jd(now.tt-3/24)
        end=self.ts.tt_jd(now.tt+self.pass_search_days)
        times,events=self.sat.find_events(self.observer,start,end,altitude_degrees=0)
        return [(times[i],int(events[i])) for i in range(len(events))]

    def update_pass_information(self,now):
        if not self.sat or not self.observer:return
        events=self.find_pass_events()
        active_aos=None
        active_los=None
        next_aos=None
        next_los=None

        for i,(t,event) in enumerate(events):
            if event!=0:continue
            aos=t
            los=None
            for t2,event2 in events[i+1:]:
                if event2==2:
                    los=t2
                    break
            if los is None:continue
            if aos.tt<=now.tt<=los.tt:
                active_aos=aos
                active_los=los
                break
            if aos.tt>now.tt:
                next_aos=aos
                next_los=los
                break

        if active_aos is not None:
            self.current_aos=active_aos
            self.current_los=active_los
            self.aos.set(self.local_time(active_aos))
            self.los.set(self.local_time(active_los))
            seconds=(active_los.utc_datetime()-now.utc_datetime()).total_seconds()
            self.countdown.set("LOS "+self.format_time(max(0,seconds)))
            return

        if next_aos is not None:
            self.current_aos=next_aos
            self.current_los=next_los
            self.aos.set(self.local_time(next_aos))
            self.los.set(self.local_time(next_los))
            seconds=(next_aos.utc_datetime()-now.utc_datetime()).total_seconds()
            self.countdown.set(self.format_time(max(0,seconds)))
            return

        self.current_aos=None
        self.current_los=None
        self.aos.set("--:--:--")
        self.los.set("--:--:--")
        self.countdown.set("---")

    def local_time(self,t):
        return t.utc_datetime().astimezone(self.local_tz).strftime("%H:%M:%S")

    def update_display(self):
        if not self.running:return
        try:
            if self.sat and self.observer:
                now=self.ts.now()
                difference=self.sat-self.observer
                topocentric=difference.at(now)
                alt,az,distance=topocentric.altaz()
                self.az.set(f"{az.degrees:03.0f}°")
                self.el.set(f"{alt.degrees:4.1f}°")
                self.range_km.set(f"{distance.km:,.0f} km")
                radial_velocity,_=self.get_range_rate(now)
                heard_rx=None

                if self.websdr_on and self.websdr and self.websdr.is_ready():
                    heard_rx=self.websdr.get_frequency()
                    self.websdr_rx_frequency=heard_rx if heard_rx is not None else self.websdr_rx_frequency

                if heard_rx is not None:
                    current_rx,current_tx,actual_rx,actual_tx,rx_doppler,tx_doppler=self.calculate_tracking_frequencies(radial_velocity,heard_rx)
                    self.rx.set(f"{current_rx/1e6:.5f} MHz")
                    self.tx.set(f"{current_tx/1e6:.5f} MHz")
                    self.actual_rx.set(f"{actual_rx/1e6:.5f} MHz")
                    self.actual_tx.set(f"{actual_tx/1e6:.5f} MHz")
                    self.doppler_rx.set(f"{rx_doppler:+.0f} Hz")
                    self.doppler_tx.set(f"{tx_doppler - self.tx_offset.get():+.0f} Hz")

                    if self.ic705:
                        try:
                            self.ic705.set_freq(int(round(current_tx)))
                            self.ic705.set_mode(self.mode.get())
                        except Exception as e:
                            print(f"IC-705 tracking error: {e}")

                    self.status.set(f"● {self.satellite_name.get()} PASS ACTIVE" if alt.degrees>=0 else "Waiting Passage")
                else:
                    self.rx.set("--- MHz")
                    self.tx.set("--- MHz")
                    self.actual_rx.set("--- MHz")
                    self.actual_tx.set("--- MHz")
                    self.doppler_rx.set("--- Hz")
                    self.doppler_tx.set("--- Hz")
                    self.status.set(f"● {self.satellite_name.get()} PASS ACTIVE — WebSDR waiting" if alt.degrees>=0 else "Waiting for WebSDR RX")

                self.update_pass_information(now)

        except Exception as e:
            self.status.set(f"Tracking error: {e}")
            print(f"Tracking error: {e}")

        self.root.after(self.update_ms,self.update_display)

    @staticmethod
    def format_time(seconds):
        seconds=int(seconds)
        h,seconds=divmod(seconds,3600)
        m,s=divmod(seconds,60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def close(self):
        self.running=False
        if self.websdr:
            try:self.websdr.stop()
            except Exception:pass
            self.websdr=None
        self.websdr_on=False
        if self.ic705:
            try:self.ic705.close()
            except Exception:pass
        self.root.destroy()

if __name__=="__main__":
    root=tk.Tk()
    app=SatTracker(root)
    root.protocol("WM_DELETE_WINDOW",app.close)
    root.mainloop()