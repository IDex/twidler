from kivy.app import App
from kivy.uix.widget import Widget

class Twidler(Widget):
    pass

class TwidlerApp(App):
    def build(self):
        return Twidler()

if __name__ == '__main__':
    main()
