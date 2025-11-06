from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.core.window import Window
import pandas as pd

Window.size = (350, 600)


# ---------------------------
# LOGIN SCREEN
# ---------------------------
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        layout.add_widget(Label(text="🔐 AI Shift Manager Login", font_size=20))

        self.username = TextInput(hint_text='Username', multiline=False)
        self.password = TextInput(hint_text='Password', password=True, multiline=False)
        layout.add_widget(self.username)
        layout.add_widget(self.password)

        btn_login = Button(text="Login", on_press=self.check_login)
        layout.add_widget(btn_login)

        self.message = Label(text="")
        layout.add_widget(self.message)

        self.add_widget(layout)

    def check_login(self, instance):
        users = pd.read_csv('users.csv')
        uname = self.username.text.strip()
        pwd = self.password.text.strip()
        user = users[(users['username'] == uname) & (users['password'] == pwd)]
        if not user.empty:
            role = user.iloc[0]['role']
            App.get_running_app().username = uname
            if role == 'manager':
                self.manager.current = 'manager'
            else:
                self.manager.current = 'employee'
        else:
            self.message.text = "❌ Invalid credentials!"


# ---------------------------
# MANAGER DASHBOARD
# ---------------------------
class ManagerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme = "light"
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Top bar
        top_bar = BoxLayout(size_hint=(1, None), height=50, spacing=5)
        top_bar.add_widget(Label(text="👨‍💼 Manager Dashboard", font_size=18))
        self.btn_theme = Button(text="🌙", size_hint=(None, 1), width=50, on_press=self.toggle_theme)
        top_bar.add_widget(self.btn_theme)
        self.layout.add_widget(top_bar)

        # Scroll area
        self.scroll = ScrollView(size_hint=(1, 0.7))
        self.grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        # Action buttons
        buttons = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        buttons.add_widget(Button(text='🔁 Refresh', on_press=lambda x: self.display_shifts()))
        buttons.add_widget(Button(text='🔄 Auto Reassign', on_press=self.reassign_shifts))
        buttons.add_widget(Button(text='📊 Analytics', on_press=self.show_analytics))
        self.layout.add_widget(buttons)

        # Logout
        self.layout.add_widget(Button(text="🚪 Logout", on_press=self.logout))

        self.add_widget(self.layout)
        self.display_shifts()

    def on_pre_enter(self, *args):
        self.display_shifts()

    def load_data(self):
        self.shifts = pd.read_csv('shifts.csv')
        self.employees = pd.read_csv('employees.csv')

    def display_shifts(self):
        self.grid.clear_widgets()
        self.load_data()

        # 🔄 Sync attendance with shift status
        for i, shift in self.shifts.iterrows():
            emp_name = shift['assigned_to']
            emp_row = self.employees[self.employees['name'].str.lower() == emp_name.lower()]
            if not emp_row.empty:
                attendance = emp_row.iloc[0]['attendance']
                if attendance == 'absent' and shift['status'] != 'reassigned':
                    self.shifts.at[i, 'status'] = 'absent'
                elif attendance == 'present' and shift['status'] == 'absent':
                    self.shifts.at[i, 'status'] = 'active'

        self.shifts.to_csv('shifts.csv', index=False)

        # Display shifts
        for _, row in self.shifts.iterrows():
            text = f"Shift {row['shift_id']} | {row['date']} | {row['time']}\nAssigned: {row['assigned_to']} | Status: {row['status']}"
            lbl = Label(text=text, size_hint_y=None, height=80, halign='left', valign='middle')
            lbl.text_size = (320, None)
            lbl.color = (0, 0, 0, 1) if self.theme == "light" else (1, 1, 1, 1)
            self.grid.add_widget(lbl)

    def reassign_shifts(self, instance):
        self.load_data()
        users = pd.read_csv('users.csv')

        # ✅ Only reassign to employees with valid logins
        valid_users = users[users['role'] == 'employee']['username'].str.lower().tolist()

        absent = self.shifts[self.shifts['status'] == 'absent']
        reassigned = []

        for i, shift in absent.iterrows():
            available = self.employees[
                (self.employees['attendance'] == 'present') &
                (self.employees['name'].str.lower().isin(valid_users))
            ]
            if not available.empty:
                new_emp = available.sample(1).iloc[0]['name']
                self.shifts.at[i, 'assigned_to'] = new_emp
                self.shifts.at[i, 'status'] = 'reassigned'
                reassigned.append((shift['shift_id'], new_emp))
            else:
                self.shifts.at[i, 'status'] = 'pending'
                reassigned.append((shift['shift_id'], "⚠️ No valid employee available"))

        self.shifts.to_csv('shifts.csv', index=False)
        self.display_shifts()

        if reassigned:
            msg = "\n".join([f"Shift {sid} → {emp}" for sid, emp in reassigned])
            self.notify("✅ Reassignment Complete", msg)
        else:
            self.notify("ℹ️ No Absentees", "All employees are present.")

    def notify(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def show_analytics(self, instance):
        self.load_data()
        total = len(self.shifts)
        active = len(self.shifts[self.shifts['status'] == 'active'])
        absent = len(self.shifts[self.shifts['status'] == 'absent'])
        reassigned = len(self.shifts[self.shifts['status'] == 'reassigned'])
        msg = f"📊 Total: {total}\n✅ Active: {active}\n❌ Absent: {absent}\n🔄 Reassigned: {reassigned}"
        self.notify("Shift Analytics", msg)

    def toggle_theme(self, instance):
        if self.theme == "light":
            # 🌙 Switch to Dark Theme
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
            self.theme = "dark"
            self.btn_theme.text = "☀️"
            text_color = (1, 1, 1, 1)
        else:
            # ☀️ Switch to Light Theme
            Window.clearcolor = (1, 1, 1, 1)
            self.theme = "light"
            self.btn_theme.text = "🌙"
            text_color = (0, 0, 0, 1)

        # Apply color to all labels
        for widget in self.walk():
            if isinstance(widget, Label):
                widget.color = text_color

    def logout(self, instance):
        self.manager.current = 'login'


# ---------------------------
# EMPLOYEE DASHBOARD
# ---------------------------
class EmployeeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme = "light"
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.title = Label(text="👷 Employee Dashboard", font_size=20)
        self.layout.add_widget(self.title)

        self.scroll = ScrollView(size_hint=(1, 0.7))
        self.grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scroll.add_widget(self.grid)
        self.layout.add_widget(self.scroll)

        btns = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        btns.add_widget(Button(text="✅ Mark Present", on_press=self.mark_present))
        btns.add_widget(Button(text="❌ Mark Absent", on_press=self.mark_absent))
        self.layout.add_widget(btns)

        theme_logout = BoxLayout(size_hint=(1, None), height=50, spacing=10)
        self.btn_theme = Button(text="🌙", on_press=self.toggle_theme)
        theme_logout.add_widget(self.btn_theme)
        theme_logout.add_widget(Button(text="🚪 Logout", on_press=self.logout))
        self.layout.add_widget(theme_logout)

        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.display_my_shifts()

    def display_my_shifts(self):
        self.grid.clear_widgets()
        shifts = pd.read_csv('shifts.csv')
        username = App.get_running_app().username.lower()

        my_shifts = shifts[shifts['assigned_to'].str.lower() == username]
        reassigned_from_me = shifts[
            (shifts['status'] == 'reassigned') &
            (~shifts['assigned_to'].str.lower().eq(username))
        ]

        found = False
        if not my_shifts.empty:
            found = True
            for _, row in my_shifts.iterrows():
                text = f"Shift {row['shift_id']} | {row['date']} | {row['time']}\nStatus: {row['status']}"
                lbl = Label(text=text, size_hint_y=None, height=80)
                lbl.color = (0, 0, 0, 1) if self.theme == "light" else (1, 1, 1, 1)
                self.grid.add_widget(lbl)
        elif not reassigned_from_me.empty:
            found = True
            last_shift = reassigned_from_me.iloc[-1]
            reassigned_to = last_shift['assigned_to']
            text = f"Your shift (Shift {last_shift['shift_id']}) has been reassigned to {reassigned_to}."
            lbl = Label(text=text, size_hint_y=None, height=100)
            lbl.color = (0, 0, 0, 1) if self.theme == "light" else (1, 1, 1, 1)
            self.grid.add_widget(lbl)
        if not found:
            lbl = Label(text="No shifts assigned yet.", size_hint_y=None, height=80)
            lbl.color = (0, 0, 0, 1) if self.theme == "light" else (1, 1, 1, 1)
            self.grid.add_widget(lbl)

    def mark_present(self, instance):
        uname = App.get_running_app().username
        df = pd.read_csv('employees.csv')
        df.loc[df['name'].str.lower() == uname.lower(), 'attendance'] = 'present'
        df.to_csv('employees.csv', index=False)

        shifts = pd.read_csv('shifts.csv')
        for i, row in shifts.iterrows():
            if row['assigned_to'].lower() == uname.lower() and row['status'] == 'absent':
                shifts.at[i, 'status'] = 'active'
        shifts.to_csv('shifts.csv', index=False)

        self.notify("✅ Attendance", "You are marked Present.")
        self.display_my_shifts()

    def mark_absent(self, instance):
        uname = App.get_running_app().username
        df = pd.read_csv('employees.csv')
        df.loc[df['name'].str.lower() == uname.lower(), 'attendance'] = 'absent'
        df.to_csv('employees.csv', index=False)

        shifts = pd.read_csv('shifts.csv')
        for i, row in shifts.iterrows():
            if row['assigned_to'].lower() == uname.lower() and row['status'] != 'reassigned':
                shifts.at[i, 'status'] = 'absent'
        shifts.to_csv('shifts.csv', index=False)

        self.notify("❌ Attendance", "You are marked Absent.")
        self.display_my_shifts()

    def notify(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def toggle_theme(self, instance):
        if self.theme == "light":
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
            self.theme = "dark"
            self.btn_theme.text = "☀️"
            text_color = (1, 1, 1, 1)
        else:
            Window.clearcolor = (1, 1, 1, 1)
            self.theme = "light"
            self.btn_theme.text = "🌙"
            text_color = (0, 0, 0, 1)

        for widget in self.walk():
            if isinstance(widget, Label):
                widget.color = text_color

    def logout(self, instance):
        self.manager.current = 'login'


# ---------------------------
# MAIN APP
# ---------------------------
class ShiftApp(App):
    username = ""

    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ManagerScreen(name='manager'))
        sm.add_widget(EmployeeScreen(name='employee'))
        return sm


if __name__ == '__main__':
    ShiftApp().run()
