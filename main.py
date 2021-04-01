import tkinter as tk
import threading
from tkinter import *
from pytube import YouTube, Playlist
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os
import time
import numpy as np
from ffpyplayer.player import MediaPlayer
from icons import icon, blank
import base64, io

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.geometry("640x420")
        self.winfo_toplevel().title("YouTube downloader")
        #Create icon from base64 string
        icon_file = io.BytesIO(base64.b64decode(icon))
        img = Image.open(icon_file, mode='r')
        self.master.iconphoto(True, ImageTk.PhotoImage(image=img))

        self.video_link = tk.StringVar()        #Link to the youtube video
        self.download_path = tk.StringVar()     #Folder to download videos to
        self.video_folder = tk.StringVar()      #Represents the folder to play videos from
        self.selected_video = 0                 #Current playing video, idx
        self.playlist = []                      #Array of video's to play
        self.downloadLeft = [0,0]
        self.download_count = None              #Download count text widget
        self.video_list = None
        self.video_embed = None
        #Styles
        self.mainBgColor = "#121212"
        self.labelBgColor = "#1E1E1E"
        self.fontColor = "white"
        self.btnHighlight = "#FF00FF"
        
        
        #Video player
        self.video_player = None
        #Create blank image for video player
        img_str = io.BytesIO(base64.b64decode(blank))
        img = Image.open(img_str, mode='r')
        self.blank_img = ImageTk.PhotoImage(image=img)

        #Play/Stop video buttons
        self.playButton = None
        self.stopButton = None
        self.pauseButton = None
        self.playlistChanged = False            #Flag for seeing whether playlist has changed
        self.songChanged = False                #Flag for seeing if user pressed next button
        self.playback_buttons_frame = None      #Bind the playback buttons frame for swapping buttons inside of it
        self.isPlaying = False                  #Flag used seeing if video is being streamed (Used in next/prev song, not in thread termination!)
        self.curVolume = 50
        self.curBassBoost = 0                   #Maybe used one day
        self.now_playing = ""

        self.master.resizable(False, False)
        self.create_widgets()
        self.fps = 30

    def create_widgets(self):
        self.master.config(bg=self.mainBgColor)
        
        ##DOWNLOADING
        download_frame = LabelFrame(self.master, bg=self.mainBgColor, width=20)
        download_frame.grid(row=0, column=0, pady=10)
        
        #Input/Link frame
        input_frame = LabelFrame(download_frame, bg=self.mainBgColor, bd=0)
        input_frame.grid(row=0,column=0,padx=5)

        link_lable = tk.Label(input_frame, text="YouTube link: ", width=10, bg=self.mainBgColor, fg=self.fontColor)
        link_lable.grid(row=1, column=0, pady=5, padx=20)

        self.master.linkText = tk.Entry(input_frame, width=54, textvariable=self.video_link, bg=self.labelBgColor, fg=self.fontColor)
        self.master.linkText.grid(row=1, column=1, padx=2)

        #destination frame (for better button positioning)
        destination_frame = LabelFrame(download_frame, bg=self.mainBgColor, bd=0)
        destination_frame.grid(row=2, column=0)

        destination_label = tk.Label(destination_frame, text="Destination: ", width=10, bg=self.mainBgColor, fg=self.fontColor)
        destination_label.grid(row=0, column=0, padx=20)

        self.master.destinationText = tk.Entry(destination_frame, width=40, textvariable=self.download_path, bg=self.labelBgColor, fg=self.fontColor)
        self.master.destinationText.grid(row=0,column=1, padx=(4,0))

        browse_B = tk.Button(destination_frame, text="Browse", command=self.BrowseDestination, width=10,bg=self.labelBgColor,fg=self.fontColor, activebackground=self.btnHighlight, activeforeground="black")
        browse_B.grid(row=0, column=2, padx=4)
        
        #Download frame
        download_btn_frame = LabelFrame(download_frame, bg=self.mainBgColor, bd=0)
        download_btn_frame.grid(row=3, column=0)

        download_b = tk.Button(download_btn_frame, text="Download", command=self.Download, width=20, bg=self.labelBgColor, fg="white", activebackground=self.btnHighlight, activeforeground="black")
        download_b.grid(row=0,column=0)

        self.download_count = tk.Text(download_btn_frame, width=22, height=1, bg=self.mainBgColor, fg="white", bd=0)
        self.download_count.grid(row=0, column=1, padx=5)
        self.download_count.insert(tk.END, "Download status: ")
        self.download_count.insert(tk.END, self.downloadLeft[0])
        self.download_count.insert(tk.END, " / ")
        self.download_count.insert(tk.END, self.downloadLeft[1])

        ##VIDEO PLAYER

        #Playback buttons and volume sliders container
        playback_container_frame = LabelFrame(self.master, bg=self.mainBgColor, bd=0)
        playback_container_frame.grid(row=1, column=0, pady=5)

        #Container that has bottom and top frame for playback buttons
        buttons_container = LabelFrame(playback_container_frame, bg=self.mainBgColor, bd=0)
        buttons_container.grid(row=0, column=0)

        #Top frame (Empty)
        top_frame = LabelFrame(buttons_container, bg=self.mainBgColor, height=22, bd=0)
        top_frame.grid(row=0, column=0)
        
        self.playback_buttons_frame = LabelFrame(buttons_container, bg=self.mainBgColor, bd=0)
        self.playback_buttons_frame.grid(row=1, column=0, padx=(50,0), pady=(8,0))
        
        prevVid = tk.Button(self.playback_buttons_frame, text="Prev", 
                            command=self.PreviousVideo, width=10,
                            bg=self.labelBgColor, fg="white", 
                            activebackground=self.btnHighlight, activeforeground="black")
        
        prevVid.grid(row=0, column=0)

        self.playButton = tk.Button(self.playback_buttons_frame, text="Play", 
                                    command=self.PlayVideo, width=10, 
                                    bg=self.labelBgColor, fg="white", 
                                    activebackground=self.btnHighlight, activeforeground="black")
        self.playButton.grid(row=0, column=1)

        nextVid = tk.Button(self.playback_buttons_frame, text="Next", 
                            command=self.NextVideo, width=10, 
                            bg=self.labelBgColor, fg="white", 
                            activebackground=self.btnHighlight, activeforeground="black")
        nextVid.grid(row=0, column=2)
        
        self.pauseButton = tk.Button(self.playback_buttons_frame, text="Pause",
                                command=self.PauseVideo, width=10, 
                                bg=self.labelBgColor, fg="white", 
                                activebackground=self.btnHighlight, activeforeground="black")
 
        self.pauseButton.grid(row=0, column=3)

        #Volume slider and bass EQ
        eq_frame = LabelFrame(playback_container_frame, bg=self.mainBgColor, bd=0)
        eq_frame.grid(row=0, column=1, padx=50)
        
        volumeText = tk.Text(eq_frame, width=10, height=1, bg=self.mainBgColor, fg="white", bd=0)
        volumeText.tag_configure("center", justify="center")
        volumeText.insert("1.0", "Volume")
        volumeText.tag_add("center", "1.0", "end")
        volumeText.grid(row=0, column=0, padx=(30,0))
        volume_slider = Scale(eq_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                            bg=self.mainBgColor, bd=0,fg="white", 
                            troughcolor=self.labelBgColor, highlightbackground=self.mainBgColor, 
                            activebackground="#FF00FF", command=self.VolumeSlider, length=150)

        volume_slider.grid(row=1, column=0,padx=(30,0))
        volume_slider.set(self.curVolume)

        #EQ/Bass boost slider for future use
        #TODO:: Re-compile ffpyplayer module with custom sdl_audio_callback function call, which will take use DSP for changing the pitch of the audio
        #Bind this slider to callback the sdl_audio_callback custom function
        # bassText = tk.Text(eq_frame, width=10, height=1, bg=self.mainBgColor, fg="white", bd=0)
        # bassText.insert(tk.END, "Bass boost")
        # bassText.grid(row=0, column=1)
        # bass_slider = Scale(eq_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
        #                     bg=self.mainBgColor, bd=0, fg="white", 
        #                     troughcolor=self.labelBgColor, highlightbackground=self.mainBgColor, 
        #                     activebackground="#FF00FF")
        # bass_slider.grid(row=1, column=1)
        # bass_slider.set(self.curBassBoost)
        
        #Video stream frame
        video_player_frame = LabelFrame(self.master, bg=self.labelBgColor, bd=1)
        video_player_frame.grid(row=2, column=0, padx=17)

        self.video_embed = tk.Label(video_player_frame, text="Video", image=self.blank_img, bg=self.labelBgColor)
        self.video_embed.grid(row=0, column=0)

        self.now_playing = Text(video_player_frame, width= 50, height=1, bg=self.mainBgColor, fg="white")
        self.now_playing.insert(tk.END, "Now playing: ")
        self.now_playing.grid(row=1, column=0)

        #Video queue frame
        queue_frame = LabelFrame(video_player_frame, bg=self.labelBgColor, bd=0)
        queue_frame.grid_rowconfigure(0, weight=0)
        queue_frame.grid_columnconfigure(0, weight=1)
        queue_frame.grid(row=0, column=1)

        queue_buttons = LabelFrame(queue_frame, bg=self.labelBgColor)
        queue_buttons.grid(row=0, column=0)

        browse_In = tk.Button(queue_buttons, text="Browse", command=self.BrowseInputFolder, width=10, bg=self.labelBgColor, fg=self.fontColor, bd=1, activebackground=self.btnHighlight, activeforeground="black")
        browse_In.grid(row=0,column=1)

        playAll = tk.Button(queue_buttons, text="Select all", command=self.SelectAll, width=10, bg=self.labelBgColor, fg=self.fontColor, bd=1, activebackground=self.btnHighlight, activeforeground="black")
        playAll.grid(row=0, column=2)
        
        
        self.video_list = tk.Listbox(queue_frame, font=("Helvetica", 12), selectmode=tk.EXTENDED, exportselection=0, height=9, bg=self.labelBgColor, fg=self.fontColor, bd=0, selectbackground=self.btnHighlight)
        self.video_list.grid(row=1, column=0)
        self.video_list.bind("<<ListboxSelect>>", self.listbox_sel_callback)
        #self.video_list.bind('<Double-Button>', self.PlayVideo)            #Double clicking video causes thread exceptions for some reason

        scrollbar = Scrollbar(queue_frame, orient="vertical", command=self.video_list.yview, bg=self.labelBgColor, highlightcolor=self.btnHighlight, bd=0)
        self.video_list.config(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky='ns')

        self.curVolume = 50
        #Search bar for videos
        # search_bar = tk.Entry(queue_frame, bd=0, )
        # search_bar.grid(row=2,column=0)

    def listbox_sel_callback(self, event):
        self.playlist = []
        indices = self.video_list.curselection()
        for i in indices:
            self.playlist.append(self.video_list.get(i))
        self.playlistChanged = True
            

    def BrowseInputFolder(self):
        video_dir = filedialog.askdirectory(initialdir="C:\\YoutubeVideos")
        self.video_folder.set(video_dir)
        self.video_list.delete(0, tk.END)
        for root, dirs, files in os.walk(self.video_folder.get()):
            for filename in files:
                self.video_list.insert(tk.END, filename)
            

    def PlayVideo(self):
        global stop_thread
        stop_thread = True
        time.sleep(0.05)         #Dangerous way of waiting for thread lol
        stop_thread = False
        self.isPlaying = True
        self.playlistChanged = False

        # if self.selected_video >= 0 and self.selected_video < len(self.playlist):
        self.start_videostream()
        #self.video_player.set_volume(float(self.curVolume)/100)
        thread = threading.Thread(target=self.Video_data_stream)
        thread.daemon = 1
        thread.start()
        self.playButton.grid_forget()
        self.stopButton = tk.Button(self.playback_buttons_frame, text="Stop", command=self.StopVideo, width=10, bg="#FF00FF", fg="black")
        self.stopButton.grid(row=0, column=1)

        #Change the "now playing"
        self.changeNowPlaying()

    def changeNowPlaying(self):
        self.now_playing.delete("1.0", tk.END)
        self.now_playing.insert(tk.END, "Now playing: ")
        if self.isPlaying:
            self.now_playing.insert(tk.END, self.playlist[self.selected_video])

    def StopVideo(self):
        global stop_thread
        global pause_thread
        self.isPlaying = False
        stop_thread = True
        pause_thread = True
        self.PauseVideo()

        self.stopButton.grid_forget()
        self.playButton = tk.Button(self.playback_buttons_frame, text="Play", command=self.PlayVideo, width=10, bg=self.labelBgColor, fg=self.fontColor)
        self.playButton.grid(row=0, column=1)
        self.changeNowPlaying()

    def PauseVideo(self):
        global pause_thread
        if pause_thread:
            #Why isn't this done in play/stop aswell lol
            self.pauseButton.config(text="Pause", bg=self.labelBgColor, fg="white")
            pause_thread = False
            self.video_player.set_pause(False)
        else:
            self.pauseButton.config(text="Unpause", bg=self.btnHighlight, fg="black")
            pause_thread = True
            self.video_player.set_pause(True)

    def start_videostream(self):
        #Start new instance of player
        if self.video_player:
            self.video_player.close_player()
        cVol = float(self.curVolume)/100
        print(cVol)
        self.video_player = MediaPlayer(self.video_folder.get() + "\\" + self.playlist[self.selected_video], ff_opts={'paused': True,'volume':0.03})
        self.video_player.set_size(400, 200)
        #while not self.video_player:
        #    continue
        time.sleep(0.1)
        if self.video_player:
            self.video_player.set_volume(cVol)
        self.video_player.set_pause(False)


    def NextVideo(self):
        if self.isPlaying == False:
            return
        #Destroy current player if there's one
        self.video_player.close_player()

        #Inform the video stream that video was changed
        self.songChanged = True
        
        #If playlist was changed, reset the index to 0
        if self.playlistChanged:
            self.selected_video = 0
            self.playlistChanged = False
        #Other wise just increment idx or start from 0 idx
        elif self.selected_video < len(self.playlist)-1:
            self.selected_video += 1
        else:
            self.selected_video = 0

        self.start_videostream()
        #self.video_player.set_volume(float(self.curVolume)/100)
        self.changeNowPlaying()
    
    def PreviousVideo(self):
        if self.isPlaying == False:
            return
        
        #Destroy current player if there's one
        self.video_player.close_player()

        self.songChanged = True

        if self.playlistChanged:
            self.selected_video = 0
            self.playlistChanged = False
        elif self.selected_video > 0:
            self.selected_video -= 1
        else:
            self.selected_video = len(self.playlist)-1

        self.start_videostream() 
        self.changeNowPlaying()

    def SelectAll(self):
        #Select every line in listbox / Every video from list
        for i in range(0, self.video_list.size()):
            self.video_list.selection_set(i)
        #Since manual selection doesn't call callback functions, just add them to playlist manually
        self.playlist = []
        indices = self.video_list.curselection()
        for i in indices:
            self.playlist.append(self.video_list.get(i))
        self.playlistChanged = True
    
    def VolumeSlider(self, value):
        if self.video_player:
            self.video_player.set_volume(float(value)/100)
        self.curVolume = value

    def Video_data_stream(self):
        global stop_thread
        global pause_thread
        stop_thread = False
        pause_thread = False

        #Start video/audio stream
        #todo:: len(self.playlist will change)
        while True:
            try:
                    
                frame, val = self.video_player.get_frame()
                if val == 'eof':
                    self.video_player.close_player()
                    self.NextVideo()        #Increment the video index
                    self.video_player.set_volume(float(self.curVolume)/100)
                    #If we still have videos left in playlist, play another one
                    # if self.selected_video < len(self.playlist):
                    #     self.video_player = MediaPlayer(self.video_folder.get() + "\\" + self.playlist[self.selected_video])
                    #     self.video_player.set_size(400, 200)
                elif frame is None:
                    time.sleep(0.01)
                else:
                    image, t = frame
                    w, h = image.get_size()
                    img = np.asarray(image.to_bytearray()[0]).reshape(h,w,3)
                    the_frame = ImageTk.PhotoImage(Image.fromarray(img))
                    self.video_embed.config(image=the_frame)
                    self.video_embed.image = the_frame
                    if stop_thread:
                        self.video_player.close_player()
                        #Reset the embed image
                        self.video_embed.config(image=self.blank_img)
                        return
                    while pause_thread:
                        #Do nothing
                        if stop_thread:
                            pause_thread = False
                            return
                        continue
                    if val <= 1:
                        time.sleep(val)
            except:
                #Exception (e.g outside thread changes to player can cause exception)
                continue

                

    def BrowseDestination(self):
        download_directory = filedialog.askdirectory(initialdir="C:\\YoutubeVideos")
        self.download_path.set(download_directory)

    def Download(self):
        self.Update_Download_Status()
        
        link = self.video_link.get()
        download_folder = self.download_path.get()
        if "list" in link:
            playlist = Playlist(link)
            thread = threading.Thread(target=self.Download_Playlist, args=(playlist, download_folder,))
            thread.daemon = 1
            thread.start()
        else:
            thread = threading.Thread(target=self.Download_Single, args=(link, download_folder,))
            thread.daemon = 1
            thread.start()            

    def Download_Playlist(self, playlist, folder):
        self.downloadLeft = [0, len(playlist.video_urls)]
        for url in playlist.video_urls:
            self.Update_Download_Status()
            try:                
                getVideo = YouTube(url)
                video_stream_buffer = getVideo.streams.first()
                video_stream_buffer.download(folder)
                self.downloadLeft[0] += 1
            except:
                if self.downloadLeft[1] > 0:
                    self.downloadLeft[1] -= 1
                continue
        self.Update_Download_Status()
        messagebox.showinfo("Download complete!","Downloaded videos from playlist to:\n" + folder)
    
    def Download_Single(self, link, folder):
        self.downloadLeft = [0,1]
        try:
            self.Update_Download_Status()
            getVideo = YouTube(link)

            video_stream_buffer = getVideo.streams.first()
            video_stream_buffer.download(folder)
            self.downloadLeft = [1,1]
            messagebox.showinfo("Download complete!","Downloaded video to:\n" + folder)
        except:
            messagebox.showinfo("Download failed!", "Video not available:\n" + folder)
        self.Update_Download_Status()

    def Update_Download_Status(self):
        self.download_count.delete('1.0', tk.END)
        self.download_count.insert(tk.END, "Download status: ")
        self.download_count.insert(tk.END, self.downloadLeft[0])
        self.download_count.insert(tk.END, " / ")
        self.download_count.insert(tk.END, self.downloadLeft[1])


stop_thread = False
pause_thread = False
root = tk.Tk()
app = Application(master=root)
app.mainloop()