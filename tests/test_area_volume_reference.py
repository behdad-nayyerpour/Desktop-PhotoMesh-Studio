"""Known-answer projected areas and 2.5D volumes above/below a boundary plane."""
import math

import numpy as np
import pytest

from photomesh import shapes as S


def rectangle(width=4.,height=3.,origin=(0.,0.,0.)):
    ring=np.array([[0,0,0],[width,0,0],[width,height,0],[0,height,0]],float)+origin
    return S.make_shape(0,'polygon',[S._close(ring)])


@pytest.mark.parametrize('origin',[(0.,0.,0.),(500000.,4500000.,100.)])
@pytest.mark.parametrize('size',[.1,1.,4.])
def test_area_and_closed_perimeter_are_translation_invariant(origin,size):
    result=S.measure(rectangle(size,size,origin))
    assert result['Area 2D']==pytest.approx(size*size,rel=0,abs=1e-8)
    assert result['Perimeter 2D']==pytest.approx(4*size,rel=0,abs=1e-8)


@pytest.mark.parametrize('mode,cut,fill,net,area3d',[
    ('block',24.,0.,24.,12.),('excavation',0.,24.,-24.,12.),
    ('prism',24.,0.,24.,12*math.sqrt(2)),
    ('balanced',6.,6.,0.,12*math.sqrt(2)),
    ('unbalanced',13.5,1.5,12.,12*math.sqrt(2)),
    ('sloping_base',24.,0.,24.,12*math.sqrt(1.05)),
])
def test_analytic_height_volumes_against_known_boundary_plane(mode,cut,fill,net,area3d):
    def sample(x,y):
        boundary=(x<=0)|(x>=4)|(y<=0)|(y>=3)
        base=100+.2*x-.1*y if mode=='sloping_base' else np.zeros_like(x)
        dz={'block':lambda:np.full_like(x,2.),'excavation':lambda:np.full_like(x,-2.),
            'prism':lambda:x,'balanced':lambda:x-2,'unbalanced':lambda:x-1,
            'sloping_base':lambda:np.full_like(x,2.)}[mode]()
        return base+np.where(boundary,0.,dz)
    result=S.measure(rectangle(),S.HeightSampler('raster',sample,.05,'analytic reference'))
    for key,expected in [('Area 2D',12.),('Area 3D (surface)',area3d),
                         ('Volume above plane (cut)',cut),('Volume below plane (fill)',fill),('Volume net',net)]:
        assert result[key]==pytest.approx(expected,rel=0,abs=1e-7),(mode,key,result[key],expected)


def test_polygon_hole_excludes_area_and_volume():
    outer=np.array([[0,0,0],[4,0,0],[4,4,0],[0,4,0],[0,0,0]],float)
    hole=np.array([[1,1,0],[3,1,0],[3,3,0],[1,3,0],[1,1,0]],float)
    shape=S.make_shape(0,'polygon',[outer,hole],holes=[False,True])
    def sample(x,y):return np.where((x==0)|(x==4)|(y==0)|(y==4),0.,2.)
    result=S.measure(shape,S.HeightSampler('raster',sample,.05,'analytic reference'))
    assert result['Area 2D']==12
    assert result['Volume above plane (cut)']==pytest.approx(24.,rel=0,abs=1e-7)


def test_one_row_surface_grid_reports_limitation_instead_of_crashing():
    result=S.measure(rectangle(4.,.14),S.HeightSampler('raster',lambda x,y:np.zeros_like(x),.1,'coarse DEM'))
    assert 'Volume' in result and isinstance(result['Volume'],str)
    assert 'Volume net' not in result


def test_missing_surface_does_not_report_zero_volume():
    result=S.measure(rectangle(),S.HeightSampler('raster',lambda x,y:np.full_like(x,np.nan),.1,'NoData'))
    assert result['Volume']=='no surface inside the polygon'
    assert 'Volume net' not in result


def test_cube_volume_and_sloping_plane_surface_area():
    def cube(x,y):return np.where((x==0)|(x==2)|(y==0)|(y==2),0.,2.)
    result=S.measure(rectangle(2.,2.),S.HeightSampler('raster',cube,.05,'cube roof'))
    assert result['Volume above plane (cut)']==pytest.approx(8.,rel=0,abs=1e-9)
    plane=S.measure(rectangle(),S.HeightSampler('raster',lambda x,y:100+2*x,.05,'plane'))
    assert plane['Area 3D (surface)']==pytest.approx(12*math.sqrt(5),rel=0,abs=1e-8)
    assert abs(plane['Volume net'])<1e-8


def test_unclosed_api_ring_is_measured_without_mutating_source():
    ring=np.array([[500000.,4500000.,0],[500004.,4500000.,0],
                   [500004.,4500003.,0],[500000.,4500003.,0]])
    shape=S.make_shape(0,'polygon',[ring]);before=ring.copy()
    result=S.measure(shape)
    assert result['Area 2D']==12 and result['Perimeter 2D']==14
    np.testing.assert_array_equal(ring,before)
    assert len(shape['parts'][0])==4


def test_triangle_volume_refinement_stays_within_boundary_cell_error():
    triangle=np.array([[0.,0.,0.],[4.,0.,0.],[0.,3.,0.],[0.,0.,0.]])
    shape=S.make_shape(0,'polygon',[triangle])
    errors=[]
    for step in (.1,.025):
        def roof(x,y):return np.where((x==0)|(y==0)|(abs(x/4+y/3-1)<1e-12),0.,2.)
        result=S.measure(shape,S.HeightSampler('raster',roof,step,'triangular prism roof'))
        assert result['Area 2D']==6
        error=abs(result['Volume above plane (cut)']-12)
        # Boundary cells can differ by at most a half-diagonal strip around
        # the triangle (perimeter 12); this is a grid approximation, not exact.
        bound=2*(12*step/math.sqrt(2)+math.pi*step*step/2)
        assert error<=bound
        errors.append(error)
    assert errors[1]<=errors[0]+1e-9


def test_partial_nodata_exposes_coverage():
    def surface(x,y):
        z=np.where((x==0)|(x==4)|(y==0)|(y==3),0.,2.)
        return np.where((x>2)&(y>0)&(y<3),np.nan,z)
    result=S.measure(rectangle(),S.HeightSampler('raster',surface,.05,'partial coverage'))
    assert '50.0 %' in result['Surface coverage']
    assert result['Volume above plane (cut)']==pytest.approx(12.,rel=0,abs=1e-7)


def test_closed_cube_mesh_above_ground_uses_real_mesh_sampler(tmp_path):
    from photomesh.plyio import save_ply
    # A 2 x 2 x 2 cube surrounded by a ground apron. The measurement boundary
    # is on the ground, not on the cube roof: its fitted reference plane is z=0.
    cube=np.array([[x,y,z] for z in (0.,2.) for y in (0.,2.) for x in (0.,2.)])
    ground=np.array([[-1,-1,0],[3,-1,0],[-1,3,0],[3,3,0]],float)
    faces=np.array([[0,2,1],[1,2,3],[4,5,6],[5,7,6],
                    [0,1,4],[1,5,4],[2,6,3],[3,6,7],
                    [0,4,2],[2,4,6],[1,3,5],[3,7,5],
                    [8,9,10],[9,11,10]],np.int32)
    path=tmp_path/'cube_with_ground.ply'
    save_ply(str(path),np.vstack([cube,ground]),faces=faces)
    sampler=S.HeightSampler.from_mesh(str(path),[0,0,0])
    sampler.px=.1  # Explicit integration resolution, finer than this tiny mesh.
    boundary=rectangle(4.,4.,(-1.,-1.,0.))
    result=S.measure(boundary,sampler)
    # Open3D casts float32 rays from height 12. Bound accumulation of several
    # ray-height ulps across the 16 m² apron, instead of a relative tolerance.
    numerical_bound=16*4*float(np.spacing(np.float32(12.)))
    assert result['Volume above plane (cut)']==pytest.approx(8.,rel=0,abs=numerical_bound)
    assert result['Volume below plane (fill)']==pytest.approx(0.,rel=0,abs=numerical_bound)


def test_volume_at_large_survey_origin_has_same_reference_plane():
    origin=np.array([500000.,4500000.,100.])
    def sample(x,y):
        x=x-origin[0];y=y-origin[1]
        inside=(x>0)&(x<4)&(y>0)&(y<3)
        return origin[2]+.2*x-.1*y+np.where(inside,2.,0.)
    result=S.measure(rectangle(4.,3.,origin),S.HeightSampler('raster',sample,.05,'UTM reference'))
    assert result['Area 2D']==12
    assert result['Volume above plane (cut)']==pytest.approx(24.,rel=0,abs=1e-6)
    assert result['Volume below plane (fill)']==pytest.approx(0.,rel=0,abs=1e-6)
