class Paginator:
    def __init__(self, items, per_page=10): self.items,self.per_page=items,per_page
    @property
    def pages(self): return max(1,(len(self.items)+self.per_page-1)//self.per_page)
    def page(self,n): return self.items[(n-1)*self.per_page:n*self.per_page]
