import React from 'react';
import {render,screen,fireEvent,waitFor,act} from '@testing-library/react';
import {afterEach, expect,it,vi} from 'vitest';
import {AuthProvider,useAuthContext} from '@/providers/auth-provider';
import {changePassword,getAuthToken,getUserStats} from '@/lib/api-client';
import {RiskStatistics} from '@/components/dashboard/risk-statistics';
const user={id:'a',email:'a@example.com',full_name:'Private Account A',role:'user',created_at:'2026-10-27T00:00:00Z'};
afterEach(()=>{vi.unstubAllGlobals();sessionStorage.clear();});
function Harness(){const auth=useAuthContext();return <><output data-testid="user">{auth.user?.full_name || (auth.loading ? 'loading' : 'signed out')}</output><button onClick={()=>void changePassword('old_password_2026','new_password_2026')}>Change password</button></>;}
it('changing password signs the active account out of the UI',async()=>{
  sessionStorage.setItem('jobshield_auth_token','active-token');
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>new Response(JSON.stringify(url.endsWith('/password')?{status:'ok'}:user),{status:200})));
  render(<AuthProvider><Harness/></AuthProvider>);
  await screen.findByText('Private Account A');
  fireEvent.click(screen.getByText('Change password'));
  await waitFor(()=>expect(getAuthToken()).toBeNull());
  expect(screen.getByTestId('user')).toHaveTextContent('signed out');
});
it('a stats 401 clears the expired authentication token',async()=>{
  sessionStorage.setItem('jobshield_auth_token','expired-token');
  vi.stubGlobal('fetch',vi.fn(async()=>new Response('{}',{status:401})));
  await expect(getUserStats()).rejects.toThrow();
  expect(getAuthToken()).toBeNull();
});
it('temporary getMe 503 does not destroy the active authentication token',async()=>{
  sessionStorage.setItem('jobshield_auth_token','active-token');
  vi.stubGlobal('fetch',vi.fn(async()=>new Response('{}',{status:503})));
  render(<AuthProvider><Harness/></AuthProvider>);
  await screen.findByText('signed out');
  expect(getAuthToken()).toBe('active-token');
});
it('counts the low-risk label actually emitted by the backend',()=>{
  render(<RiskStatistics stats={{total_analyses:1,saved_analyses:0,risk_distribution:{'Ít dấu hiệu rủi ro':1}}}/>);
  expect(screen.getAllByText('1')).toHaveLength(3);
});

function RaceHarness(){const auth=useAuthContext();return <><output data-testid="race-user">{auth.user?.email || 'signed out'}</output><button onClick={()=>void auth.refreshUser()}>Refresh profile</button><button onClick={()=>void auth.logout()}>Logout</button></>;}
it('a late profile response cannot restore private account data after logout',async()=>{
  sessionStorage.setItem('jobshield_auth_token','active-token');
  let readCount=0;
  let finish!: (r:Response)=>void;
  vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
    if(url.endsWith('/auth/logout'))return new Response('{}',{status:200});
    if(++readCount===1)return new Response(JSON.stringify(user),{status:200});
    return new Promise<Response>(r=>{finish=r;});
  }));
  render(<AuthProvider><RaceHarness/></AuthProvider>);
  await screen.findByText('a@example.com');
  fireEvent.click(screen.getByText('Refresh profile'));
  await waitFor(()=>expect(finish).toBeDefined());
  fireEvent.click(screen.getByText('Logout'));
  await screen.findByText('signed out');
  await act(async()=>{finish(new Response(JSON.stringify(user),{status:200}));});
  expect(getAuthToken()).toBeNull();
  expect(screen.getByTestId('race-user')).toHaveTextContent('signed out');
});

import HistoryPage from '@/app/(user)/history/page';
it('deleting the only item on page 2 still gives access to the 10 remaining items',async()=>{
  const item={id:'last-item',job:{job_title:'Last page item'},risk_label_vi:'Ít dấu hiệu rủi ro',finding_vi:'Review finding',created_at:'2026-10-27T00:00:00Z',is_saved:false};
  let removed=false;
  vi.stubGlobal('confirm',vi.fn(()=>true));
  vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
    if(options?.method==='DELETE'){removed=true;return new Response('{}',{status:200});}
    const p=new URL(url,'http://localhost').searchParams.get('page');
    const firstPage=Array.from({length:10},(_,index)=>({...item,id:`first-${index}`,job:{job_title:index?'History item '+index:'First page item'}}));
    return new Response(JSON.stringify({items:p==='2'?(removed?[]:[item]):firstPage,total:removed?10:11,page:Number(p),page_size:10}),{status:200});
  }));
  render(<HistoryPage/>);
  await screen.findByText('First page item');
  fireEvent.click(screen.getByText('Trang sau'));
  await screen.findByText('Last page item');
  fireEvent.click(screen.getByRole('button',{name:'Xóa phân tích'}));
  await screen.findByText('Lịch sử phân tích (10)');
  expect(screen.queryByText('Chưa có tin tuyển dụng nào được phân tích')).not.toBeInTheDocument();
  await screen.findByText('First page item');
});

import {AuthForm} from '@/components/auth/auth-form';
import {register as registerAccount} from '@/lib/api-client';
it('shows the server validation message rather than [object Object]',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({detail:[{loc:['body','email'],msg:'Value error, Email không hợp lệ.',type:'value_error'}]}),{status:422})));
  render(<AuthForm mode="register" onSubmit={async d=>{await registerAccount(d.email,d.password,d.full_name!);}}/>);
  fireEvent.change(screen.getByLabelText('Họ và tên'),{target:{value:'Review User'}});
  fireEvent.change(screen.getByLabelText('Email'),{target:{value:'bad'}});
  fireEvent.change(screen.getByLabelText('Mật khẩu'),{target:{value:'valid_password_2026'}});
  fireEvent.click(screen.getByRole('button',{name:'Đăng ký tài khoản'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Email không hợp lệ');
});

import SavedPage from '@/app/(user)/saved/page';
it('unsaving the only item on page 2 returns to the remaining saved items',async()=>{
  const item={id:'last-item',job:{job_title:'Last saved item'},risk_label_vi:'Ít dấu hiệu rủi ro',finding_vi:'Review finding',created_at:'2026-10-27T00:00:00Z'};
  const record={analysis_id:item.id,analysis:item,saved_at:'2026-10-27T00:00:00Z'};
  let removed=false;
  vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
    if(options?.method==='DELETE'){removed=true;return new Response('{}',{status:200});}
    const p=new URL(url,'http://localhost').searchParams.get('page');
    const firstPage=Array.from({length:10},(_,index)=>({...record,analysis_id:`first-${index}`,analysis:{...item,id:`first-${index}`,job:{job_title:index?'Saved item '+index:'First saved item'}}}));
    return new Response(JSON.stringify({items:p==='2'?(removed?[]:[record]):firstPage,total:removed?10:11,page:Number(p),page_size:10}),{status:200});
  }));
  render(<SavedPage/>);
  await screen.findByText('First saved item');
  fireEvent.click(screen.getByText('Trang sau'));
  await screen.findByText('Last saved item');
  fireEvent.click(screen.getByRole('button',{name:'Bỏ lưu'}));
  await screen.findByText('Tin đã lưu (10)');
  expect(screen.queryByText('Chưa có tin tuyển dụng nào được lưu')).not.toBeInTheDocument();
  await screen.findByText('First saved item');
});
